from django.contrib import admin
from .models import (
    UserRole, Tier, Member, Staff, Maskapai, Penyedia, Mitra,
    ClaimMissingMiles, TransferMiles, Identity
)


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('role', 'description', 'created_at')
    search_fields = ('role',)


@admin.register(Tier)
class TierAdmin(admin.ModelAdmin):
    list_display = ('tier_name', 'minimal_tier_miles', 'minimal_frekuensi_terbang', 'is_active', 'created_at')
    search_fields = ('tier_name',)
    list_filter = ('is_active', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Tier Information', {
            'fields': ('tier_name', 'is_active')
        }),
        ('Tier Requirements', {
            'fields': ('minimal_tier_miles', 'minimal_frekuensi_terbang')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('member_id', 'user', 'total_miles', 'award_miles', 'tier', 'phone_number', 'is_active', 'created_at')
    search_fields = ('member_id', 'user__username', 'user__email')
    list_filter = ('is_active', 'tier', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'member_id')
        }),
        ('Personal Information', {
            'fields': ('salutation', 'phone_number', 'birth_date', 'nationality')
        }),
        ('Miles and Tier', {
            'fields': ('total_miles', 'award_miles', 'tier')
        }),
        ('Contact', {
            'fields': ('country_code',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ('staff_id', 'user', 'department', 'phone_number', 'is_active', 'created_at')
    search_fields = ('staff_id', 'user__username', 'user__email')
    list_filter = ('is_active', 'department', 'created_at')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Maskapai)
class MaskapaiAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'contact_person', 'email', 'is_active', 'created_at')
    search_fields = ('name', 'code', 'email')
    list_filter = ('is_active', 'created_at')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Penyedia)
class PenyediaAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'contact_person', 'email', 'is_active', 'created_at')
    search_fields = ('name', 'code', 'email')
    list_filter = ('is_active', 'created_at')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Mitra)
class MitraAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'contact_person', 'email', 'is_active', 'created_at')
    search_fields = ('name', 'code', 'email')
    list_filter = ('is_active', 'created_at')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ClaimMissingMiles)
class ClaimMissingMilesAdmin(admin.ModelAdmin):
    list_display = ('claim_id', 'member', 'flight_number', 'flight_date', 'miles_amount', 'status', 'created_at')
    search_fields = ('claim_id', 'member__member_id', 'flight_number', 'ticket_number')
    list_filter = ('status', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Claim Information', {
            'fields': ('claim_id', 'member', 'status')
        }),
        ('Flight Details', {
            'fields': ('flight_number', 'ticket_number', 'flight_date', 'miles_amount')
        }),
        ('Claim Details', {
            'fields': ('reason', 'description')
        }),
        ('Approval', {
            'fields': ('approved_by',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TransferMiles)
class TransferMilesAdmin(admin.ModelAdmin):
    list_display = ('transfer_id', 'from_member', 'to_member', 'miles_amount', 'status', 'created_at')
    search_fields = ('transfer_id', 'from_member__member_id', 'to_member__member_id')
    list_filter = ('status', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Transfer Information', {
            'fields': ('transfer_id', 'from_member', 'to_member', 'status')
        }),
        ('Transfer Details', {
            'fields': ('miles_amount', 'description')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Identity)
class IdentityAdmin(admin.ModelAdmin):
    list_display = ('member', 'document_number', 'document_type', 'country', 'is_expired', 'created_at')
    search_fields = ('member__member_id', 'document_number')
    list_filter = ('document_type', 'country', 'is_expired', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Identity Information', {
            'fields': ('member', 'document_number', 'document_type', 'is_expired')
        }),
        ('Document Details', {
            'fields': ('country', 'issue_date', 'expiry_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
