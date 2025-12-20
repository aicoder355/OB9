from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages

from ..models import LoyaltyProgram, ClientCategory, LoyaltyTransaction


def is_manager(user):
    return user.is_staff or user.is_superuser


@user_passes_test(is_manager)
def loyalty_dashboard(request):
    programs = LoyaltyProgram.objects.all()
    categories = ClientCategory.objects.all()
    total_points = LoyaltyTransaction.objects.aggregate(total=Sum('points'))['total'] or 0
    
    context = {
        'programs': programs,
        'categories': categories,
        'total_points': total_points,
        'active_programs': programs.filter(is_active=True).count(),
    }
    return render(request, 'loyalty/dashboard.html', context)


@user_passes_test(is_manager)
def loyalty_program_edit(request, program_id=None):
    if program_id:
        program = get_object_or_404(LoyaltyProgram, id=program_id)
    else:
        program = None
    
    if request.method == 'POST':
        name = request.POST.get('name')
        points_per_liter = request.POST.get('points_per_liter')
        points_to_money_rate = request.POST.get('points_to_money_rate')
        min_points_to_redeem = request.POST.get('min_points_to_redeem')
        is_active = request.POST.get('is_active') == 'on'
        
        if program is None:
            program = LoyaltyProgram.objects.create(
                name=name,
                points_per_liter=points_per_liter,
                points_to_money_rate=points_to_money_rate,
                min_points_to_redeem=min_points_to_redeem,
                is_active=is_active
            )
        else:
            program.name = name
            program.points_per_liter = points_per_liter
            program.points_to_money_rate = points_to_money_rate
            program.min_points_to_redeem = min_points_to_redeem
            program.is_active = is_active
            program.save()
            
        messages.success(request, 'Программа лояльности успешно сохранена')
        return redirect('loyalty_dashboard')
        
    return render(request, 'loyalty/program_form.html', {'program': program})


@user_passes_test(is_manager)
def loyalty_category_edit(request, category_id=None):
    if category_id:
        category = get_object_or_404(ClientCategory, id=category_id)
    else:
        category = None
        
    if request.method == 'POST':
        name = request.POST.get('name')
        discount_percentage = request.POST.get('discount_percentage')
        min_points_required = request.POST.get('min_points_required')
        
        if category is None:
            category = ClientCategory.objects.create(
                name=name,
                discount_percentage=discount_percentage,
                min_points_required=min_points_required
            )
        else:
            category.name = name
            category.discount_percentage = discount_percentage
            category.min_points_required = min_points_required
            category.save()
            
        messages.success(request, 'Категория клиентов успешно сохранена')
        return redirect('loyalty_dashboard')
        
    return render(request, 'loyalty/category_form.html', {'category': category})


@user_passes_test(is_manager)
def loyalty_transactions(request):
    transactions = LoyaltyTransaction.objects.select_related('client').order_by('-created_at')
    return render(request, 'loyalty/transactions.html', {'transactions': transactions})
