"""
Views for thr item API
"""
from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
    OpenApiParameter,
    OpenApiTypes,
)
from difflib import SequenceMatcher
from rest_framework import (
    viewsets,
    mixins,
    permissions,
    status,
)
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from core.models import (
    Item,
    Tag,
    Claims,
)
from item import serializers

def match_claim_to_item(claim,items):
    """Match claim to item based on description"""
    best_match = None
    best_ratio = 0

    for item in items:
        ratio = SequenceMatcher(None,claim.description.lower(),
                item.description.lower()).ratio()
        if ratio > best_ratio and ratio > 0.6:
            best_ratio = ratio
            best_match = item

    return best_match

@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                'tags',
                OpenApiTypes.STR,
                description='Comma seperated list of IDs to filter',
            )
        ]
    )
)


class ItemViewSet(viewsets.ModelViewSet):
    """View for manage recipe APIs"""
    serializer_class = serializers.ItemDetailSerializer
    queryset = Item.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def _params_to_ints(self, qs):
        """Convert a list to strings to integers."""
        return [int(str_id) for str_id in qs.split(',')]
    def get_queryset(self):
        """Retrieve items for authenticated user"""
        tags = self.request.query_params.get('tags')
        queryset = self.queryset
        if tags:
            tags_ids = self._params_to_ints(tags)
            queryset = queryset.filter(tags__id__in=tags_ids)

        return queryset.filter(
            user=self.request.user
        ).order_by('-id').distinct()

    def get_serializer_class(self):
        """Return the serializer class for request"""
        if self.action == 'list':
            return serializers.ItemSerializer
        elif self.action == 'upload_image':
            return serializers.ItemImageSerializer

        return self.serializer_class

    def perform_create(self, serializer):
        """Create a new Item"""
        serializer.save(user=self.request.user)

    @action(methods=['POST'], detail=True, url_path='upload-image')
    def upload_image(self, request, pk=None):
        """Upload an image to item"""
        item = self.get_object()
        serializer = self.get_serializer(item, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                'assigned_only',
                OpenApiTypes.INT, enum=[0, 1],
                description='Filter by items assigned to items.',
            )
        ]
    )
)


class BasicItemAPIAttrViewSet(
            mixins.DestroyModelMixin,mixins.UpdateModelMixin,
            mixins.ListModelMixin,viewsets.GenericViewSet):
    """Base viewset for item attributes"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter queryset to authenticated user"""
        assigned_only = bool(
            int(self.request.query_params.get('assigned_only',0))
        )
        queryset = self.queryset
        if assigned_only:
            queryset = queryset.filter(item__isnull=False)

        return queryset.filter(
            user=self.request.user
        ).order_by('-name').distinct()


class TagViewSet(BasicItemAPIAttrViewSet):
    """manager tags in the database."""
    serializer_class = serializers.TagSerializer
    queryset = Tag.objects.all()


class IsOwnerOrAdmin(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj.user == request.user

class ClaimsViewSet(BasicItemAPIAttrViewSet, mixins.CreateModelMixin):
    queryset = Claims.objects.none()
    serializer_class = serializers.ClaimsSerializer

    def get_queryset(self):
        if self.request.user.is_staff:
            return Claims.objects.all()
        return Claims.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        claim = serializer.save(user=self.request.user)
        items = Item.objects.all()
        matched_item = match_claim_to_item(claim, items)
        if matched_item:
            claim.item = matched_item
            claim.save()

    def get_permissions(self):
        if self.action in ['update', 'destroy']:
            return [permissions.IsAuthenticated(), IsOwnerOrAdmin()]
        elif self.action in ['partial_update']:
            if self.request.data.get('status'):
                return [permissions.IsAdminUser()]
            return [permissions.IsAuthenticated(), IsOwnerOrAdmin()]
        return super().get_permissions()
