from .models import Member, Staff


def user_type_context(request):
    """Context processor to determine and pass user type"""
    context = {}
    
    if request.user.is_authenticated:
        try:
            member = Member.objects.get(user=request.user)
            context['user_type'] = 'member'
            context['member'] = member
        except Member.DoesNotExist:
            pass
        
        try:
            staff = Staff.objects.get(user=request.user)
            context['user_type'] = 'staff'
            context['staff'] = staff
        except Staff.DoesNotExist:
            pass
    
    return context
