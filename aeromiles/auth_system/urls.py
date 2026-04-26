from django.urls import path
from . import views

app_name = 'auth_system'

urlpatterns = [
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('register/member/', views.register_member_view, name='register_member'),
    path('register/staff/', views.register_staff_view, name='register_staff'),
    path('member/claims/', views.member_claim_list_view, name='member_claim_list'),
    path('member/claims/create/', views.member_claim_create_view, name='member_claim_create'),
    path('member/claims/<int:claim_id>/', views.member_claim_detail_view, name='member_claim_detail'),
    path('member/claims/<int:claim_id>/edit/', views.member_claim_update_view, name='member_claim_update'),
    path('member/claims/<int:claim_id>/delete/', views.member_claim_delete_view, name='member_claim_delete'),
    path('staff/claims/', views.staff_claim_list_view, name='staff_claim_list'),
    path('staff/claims/<int:claim_id>/edit/', views.staff_claim_update_view, name='staff_claim_update'),
    path('member/transfers/', views.member_transfer_list_view, name='member_transfer_list'),
    path('member/transfers/create/', views.member_transfer_create_view, name='member_transfer_create'),
]
