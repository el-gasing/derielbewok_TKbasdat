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
    
    # Member Identity Management (Member only)
    path('identitas/', views.member_identities_list, name='member_identities_list'),
    path('identitas/tambah/', views.add_member_identity, name='add_member_identity'),
    path('identitas/edit/<int:identity_id>/', views.edit_member_identity, name='edit_member_identity'),
    path('identitas/hapus/<int:identity_id>/', views.delete_member_identity, name='delete_member_identity'),

    # Member: Claim Missing Miles
    path('member/claims/', views.member_claim_list_view, name='member_claim_list'),
    path('member/claims/add/', views.member_claim_create_view, name='member_claim_create'),
    path('member/claims/<int:claim_id>/', views.member_claim_detail_view, name='member_claim_detail'),
    path('member/claims/edit/<int:claim_id>/', views.member_claim_update_view, name='member_claim_update'),
    path('member/claims/delete/<int:claim_id>/', views.member_claim_delete_view, name='member_claim_delete'),

    # Staff: Claim Management
    path('staff/claims/', views.staff_claim_list_view, name='staff_claim_list'),
    path('staff/claims/edit/<int:claim_id>/', views.staff_claim_update_view, name='staff_claim_update'),

    # Member: Transfer Miles
    path('member/transfer/', views.member_transfer_list_view, name='member_transfer_list'),
    path('member/transfer/add/', views.member_transfer_create_view, name='member_transfer_create'),

    # Member: Redeem Hadiah
    path('member/redeem/', views.member_redeem_view, name='member_redeem'),

    # Member: Award Miles Package
    path('member/package/', views.member_package_view, name='member_package'),

    # Member: Tier Information
    path('member/tier/', views.member_tier_view, name='member_tier'),
]
