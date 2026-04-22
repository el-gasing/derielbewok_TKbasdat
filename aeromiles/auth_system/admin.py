from django.contrib import admin
from .models import (
    UserRole, Member, Staff, Maskapai, Penyedia, Mitra,
    ClaimMissingMiles, TransferMiles
)


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('role', 'description', 'created_at')
    search_fields = ('role',)


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('member_id', 'user', 'phone_number', 'total_miles', 'is_active', 'created_at')
    search_fields = ('member_id', 'user__username', 'user__email')
    list_filter = ('is_active', 'created_at')
    readonly_fields = ('created_at', 'updated_at')


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
    list_display = ('claim_id', 'member', 'flight_number', 'miles_amount', 'status', 'created_at')
    search_fields = ('claim_id', 'member__member_id', 'flight_number')
    list_filter = ('status', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Claim Information', {
            'fields': ('claim_id', 'member', 'status')
        }),
        ('Flight Details', {
            'fields': ('flight_number', 'flight_date', 'miles_amount')
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
