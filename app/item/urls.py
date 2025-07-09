"""
URL mappings for thr Item app
"""

from django.urls import (
    path,
    include,
)

from rest_framework.routers import DefaultRouter

from item import views

router = DefaultRouter()
router.register('items',views.ItemViewSet)
router.register('tags', views.TagViewSet)
router.register('claims', views.ClaimsViewSet, basename='claims')

app_name = 'item'

urlpatterns =[
    path('',include(router.urls)),
]
