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
    
    # Member Management (Staff only)
    path('kelola-member/', views.manage_members_list, name='manage_members_list'),
    path('kelola-member/tambah/', views.add_member, name='add_member'),
    path('kelola-member/edit/<str:member_id>/', views.edit_member, name='edit_member'),
    path('kelola-member/hapus/<str:member_id>/', views.delete_member, name='delete_member'),
]
