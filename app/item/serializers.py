"""
Serializers for item API
"""

from rest_framework import serializers

from core.models import (
    Item,
    Tag,
    Claims,
)


class TagSerializer(serializers.ModelSerializer):
    """Serializer for tags."""

    class Meta:
        model = Tag
        fields = ['id', 'name']
        read_only_fields = ['id']


class ItemSerializer(serializers.ModelSerializer):
    """Serializer for items"""
    tags = TagSerializer(many=True, required=False)

    class Meta:
        model = Item
        fields = ['id', 'title', 'description', 'status', 'category', 'location_last_seen', 'date_lost', 'tags']
        read_only_fields = ['id']

    def _get_or_create_tags(self, tags, item):
        """Handle getting or creating tags as needed"""
        auth_user = self.context['request'].user
        for tag in tags:
            tag_obj, created = Tag.objects.get_or_create(
                user=auth_user,
                **tag,
            )
            item.tags.add(tag_obj)

    def create(self, validated_data):
        """Creat an item"""
        tags = validated_data.pop('tags', [])
        item = Item.objects.create(**validated_data)
        self._get_or_create_tags(tags, item)

        return item

    def update(self, instance, validated_data):
        """Update item"""
        tags = validated_data.pop('tags', None)
        if tags is not None:
            instance.tags.clear()
            self._get_or_create_tags(tags, instance)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class ItemDetailSerializer(ItemSerializer):
    """Serializer for item detail view"""

    class Meta(ItemSerializer.Meta):
        fields = ItemSerializer.Meta.fields + ['image']


class ClaimsSerializer(serializers.ModelSerializer):
    item = serializers.SlugRelatedField(
        queryset=Item.objects.all(),
        slug_field = 'title'
    )

    class Meta:
        model = Claims
        fields = ['id','item', 'user', 'status','description' ]
        read_only_fields = ['user']


class ItemImageSerializer(serializers.ModelSerializer):
    """Serializer for uploading images to item"""

    class Meta:
        model = Item
        fields = ['id','image']
        read_only_fields = ['id']
        extra_kwargs = {'image': {'required': 'True'}}
