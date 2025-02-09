from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Profile, Category, Product, Review, Order, OrderItem

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'first_name', 'last_name')
        
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user

class UserSerializer(serializers.ModelSerializer):
    is_admin = serializers.BooleanField(source='is_staff', read_only=True)
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'is_admin')

class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = Profile
        fields = ('id', 'user', 'email', 'phone', 'address', 'created_at', 'updated_at')

class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ('id', 'name', 'description', 'image', 'product_count')
    
    def get_product_count(self, obj):
        return obj.product_set.filter(is_active=True).count()

class ReviewSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Review
        fields = ('id', 'product', 'user', 'rating', 'comment', 'created_at')
        read_only_fields = ('user',)

class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True)
    average_rating = serializers.SerializerMethodField()
    reviews = ReviewSerializer(many=True, read_only=True)
    review_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = ('id', 'name', 'description', 'price', 'category', 'category_id',
                 'stock', 'image', 'ingredients', 'usage_instructions', 'weight',
                 'is_active', 'created_at', 'updated_at', 'average_rating',
                 'reviews', 'review_count')
    
    def get_average_rating(self, obj):
        reviews = obj.reviews.all()
        if reviews:
            return round(sum(review.rating for review in reviews) / len(reviews), 1)
        return None
    
    def get_review_count(self, obj):
        return obj.reviews.count()

class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = OrderItem
        fields = ('id', 'product', 'product_id', 'quantity', 'price')

class OrderSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    items = OrderItemSerializer(many=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Order
        fields = ('id', 'user', 'status', 'status_display', 'total_amount',
                 'shipping_address', 'phone', 'items', 'created_at', 'updated_at')
        read_only_fields = ('user', 'total_amount', 'status_display')
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        order = Order.objects.create(**validated_data)
        
        total_amount = 0
        for item_data in items_data:
            product = Product.objects.get(pk=item_data['product_id'])
            if product.stock < item_data['quantity']:
                raise serializers.ValidationError(
                    f"Not enough stock for product: {product.name}")
            
            price = product.price
            quantity = item_data['quantity']
            total_amount += price * quantity
            
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                price=price
            )
            
            # Mise à jour du stock
            product.stock -= quantity
            product.save()
        
        order.total_amount = total_amount
        order.save()
        return order

class DashboardStatsSerializer(serializers.Serializer):
    total_orders = serializers.IntegerField()
    recent_orders = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    recent_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_customers = serializers.IntegerField()
    low_stock_products = serializers.IntegerField()
    top_products = ProductSerializer(many=True)
    orders_by_status = serializers.ListField(child=serializers.DictField())