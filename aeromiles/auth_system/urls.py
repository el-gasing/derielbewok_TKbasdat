from django.urls import path
from . import views

app_name = 'auth_system'

urlpatterns = [
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/settings/', views.profile_settings_view, name='profile_settings'),
    path('register/member/', views.register_member_view, name='register_member'),
    path('register/staff/', views.register_staff_view, name='register_staff'),
    path('staff/members/', views.manage_members_list_view, name='manage_members_list'),
    path('staff/members/add/', views.add_member_view, name='add_member'),
    path('staff/members/<str:member_id>/edit/', views.edit_member_view, name='edit_member'),
    path('staff/members/<str:member_id>/delete/', views.delete_member_view, name='delete_member'),
    path('member/identities/', views.member_identities_list_view, name='member_identities_list'),
    path('member/identities/add/', views.add_member_identity_view, name='add_member_identity'),
    path('member/identities/<int:identity_id>/edit/', views.edit_member_identity_view, name='edit_member_identity'),
    path('member/identities/<int:identity_id>/delete/', views.delete_member_identity_view, name='delete_member_identity'),
    path('member/redeem/', views.member_redeem_view, name='member_redeem'),
    path('member/package/', views.member_package_view, name='member_package'),
    path('member/tier/', views.member_tier_view, name='member_tier'),
    path('member/claims/', views.member_claim_list_view, name='member_claim_list'),
    path('member/claims/create/', views.member_claim_create_view, name='member_claim_create'),
    path('member/claims/<int:claim_id>/', views.member_claim_detail_view, name='member_claim_detail'),
    path('member/claims/<int:claim_id>/edit/', views.member_claim_update_view, name='member_claim_update'),
    path('member/claims/<int:claim_id>/delete/', views.member_claim_delete_view, name='member_claim_delete'),
    path('staff/claims/', views.staff_claim_list_view, name='staff_claim_list'),
    path('staff/claims/edit/<int:claim_id>/', views.staff_claim_update_view, name='staff_claim_update'),
    path('staff/rewards/', views.staff_rewards_view, name='staff_rewards'),
    path('staff/partners/', views.staff_partners_view, name='staff_partners'),
    path('staff/reports/transactions/', views.staff_transaction_report_view, name='staff_transaction_report'),
    path('staff/reports/transactions/delete/', views.staff_transaction_delete_view, name='staff_transaction_delete'),

    # Staff: Hadiah (Reward/Prize) Management
    path('staff/hadiah/', views.staff_hadiah_list_view, name='staff_hadiah_list'),
    path('staff/hadiah/create/', views.staff_hadiah_create_view, name='staff_hadiah_create'),
    path('staff/hadiah/<int:hadiah_id>/', views.staff_hadiah_detail_view, name='staff_hadiah_detail'),
    path('staff/hadiah/<int:hadiah_id>/edit/', views.staff_hadiah_update_view, name='staff_hadiah_update'),
    path('staff/hadiah/<int:hadiah_id>/delete/', views.staff_hadiah_delete_view, name='staff_hadiah_delete'),

    # Member: Transfer Miles
    path('member/transfer/', views.member_transfer_list_view, name='member_transfer_list'),
    path('member/transfer/add/', views.member_transfer_create_view, name='member_transfer_create'),

    # Staff: Mitra (Partner) Management
    path('staff/mitra/create/', views.staff_mitra_create_view, name='staff_mitra_create'),
    path('staff/mitra/<int:mitra_id>/edit/', views.staff_mitra_edit_view, name='staff_mitra_edit'),
    path('staff/mitra/<int:mitra_id>/delete/', views.staff_mitra_delete_view, name='staff_mitra_delete'),
]
