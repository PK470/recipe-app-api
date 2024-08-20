"""
URL mapping for the user API
"""
from django.urls import path
from user import view

app_name = 'user'

urlpatterns = [
    path('create/', view.CreateUserView.as_view(), name='create'),
    path('token/', view.CreateTokenView.as_view(), name = 'token'),
    path('me/', view.ManageUserView.as_view(), name='me'),
]

