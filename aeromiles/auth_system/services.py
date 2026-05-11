"""
Business logic services for AeroMiles application.
Handles duplicate checking, tier updates, and other business rules.
"""
from django.db.models import Q, Count
from .models import ClaimMissingMiles, Member, Tier


def check_duplicate_claim(member, flight_number, ticket_number, flight_date):
    """
    Check if a claim with the same flight details already exists.
    
    Duplicate check criteria:
    - Same member
    - Same flight_number
    - Same ticket_number (if provided)
    - Same flight_date
    
    Args:
        member: Member instance
        flight_number: Flight number string
        ticket_number: Ticket number string (can be None)
        flight_date: Flight date
        
    Returns:
        Existing claim or None
    """
    query = Q(
        member=member,
        flight_number__iexact=flight_number,
        flight_date=flight_date,
        status__in=['pending', 'approved']  # Only check pending and approved claims
    )
    
    if ticket_number:
        query &= Q(ticket_number__iexact=ticket_number)
    
    existing_claim = ClaimMissingMiles.objects.filter(query).first()
    return existing_claim


def get_tier_for_miles(miles):
    """
    Get the appropriate tier for a given total miles amount.
    
    Args:
        miles: Total miles amount
        
    Returns:
        Tier instance or None
    """
    tiers = Tier.objects.filter(is_active=True).order_by('-minimal_tier_miles')
    
    for tier in tiers:
        if miles >= tier.minimal_tier_miles:
            return tier
    
    return None


def update_member_tier(member):
    """
    Automatically update member's tier based on total_miles.
    
    Args:
        member: Member instance to update
        
    Returns:
        Updated Member instance
    """
    new_tier = get_tier_for_miles(member.total_miles)
    
    if new_tier != member.tier:
        member.tier = new_tier
        member.save(update_fields=['tier'])
    
    return member


def add_miles_to_member(member, miles_amount, reason=""):
    """
    Add miles to member's total_miles and update tier automatically.
    
    Args:
        member: Member instance
        miles_amount: Amount of miles to add
        reason: Optional reason for adding miles
        
    Returns:
        Updated Member instance
    """
    member.total_miles += miles_amount
    member.save(update_fields=['total_miles'])
    
    # Auto-update tier based on new total
    return update_member_tier(member)


def process_claim_approval(claim, approved_by_staff):
    """
    Process a claim approval:
    - Update claim status to 'processed'
    - Add miles to member
    - Update member tier
    
    Args:
        claim: ClaimMissingMiles instance
        approved_by_staff: Staff instance approving the claim
        
    Returns:
        Updated claim
    """
    if claim.status != 'approved':
        raise ValueError("Only approved claims can be processed.")
    
    # Update claim status
    claim.status = 'processed'
    claim.approved_by = approved_by_staff
    claim.save(update_fields=['status', 'approved_by'])
    
    # Add miles to member
    add_miles_to_member(claim.member, claim.miles_amount, f"Claim {claim.claim_id}")
    
    return claim


def validate_tier_change_eligibility(member):
    """
    Check if member is eligible for a tier change based on their miles.
    
    Args:
        member: Member instance
        
    Returns:
        dict with tier change info
    """
    new_tier = get_tier_for_miles(member.total_miles)
    current_tier = member.tier
    
    return {
        'eligible_tier': new_tier,
        'current_tier': current_tier,
        'changed': new_tier != current_tier,
        'miles': member.total_miles
    }
