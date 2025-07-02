"""
Serializers for item API
"""

from rest_framework import serializers

from core.models import Item

class ItemSerializer(serializers.ModelSerializer):
    """Serializer for items"""

    class Meta:
        model = Item
        fields = [ 'id', 'title', 'description', 'status', 'category', 'location_last_seen', 'date_lost']
        read_only_fields = ['id']


class ItemDetailSerializer(ItemSerializer):
    """Serializer for recipe detail view"""

    class Meta(ItemSerializer.Meta):
        fields = ItemSerializer.Meta.fields + ['description']
