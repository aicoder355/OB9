from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone

from ..models import Driver, Region


@login_required
def drivers(request):
    drivers_list = Driver.objects.all()
    search_query = request.GET.get('search', '')
    if search_query:
        drivers_list = drivers_list.filter(
            Q(name__icontains=search_query) |
            Q(phone__icontains=search_query)
        )
    paginator = Paginator(drivers_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'drivers.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'can_add_driver': request.user.has_perm('crm.add_driver'),
        'can_change_driver': request.user.has_perm('crm.change_driver'),
        'can_delete_driver': request.user.has_perm('crm.delete_driver'),
        'regions': Region.objects.all(),
    })


@login_required
@permission_required('crm.add_driver', raise_exception=True)
def create_driver(request):
    if request.method == 'POST':
        telegram_val = request.POST.get('telegram_chat_id') or None
        Driver.objects.create(
            name=request.POST.get('name'),
            phone=request.POST.get('phone'),
            telegram_chat_id=telegram_val,
            region_id=request.POST.get('region'),
            created_at=timezone.now()
        )
        messages.success(request, "Водитель добавлен.")
        return redirect('drivers')
    return render(request, 'drivers.html', {
        'regions': Region.objects.all(),
    })


@login_required
@permission_required('crm.change_driver', raise_exception=True)
def edit_driver(request):
    if request.method == 'POST':
        driver = Driver.objects.get(id=request.POST.get('driver_id'))
        driver.name = request.POST.get('name')
        driver.phone = request.POST.get('phone')
        driver.telegram_chat_id = request.POST.get('telegram_chat_id') or None
        driver.region_id = request.POST.get('region')
        driver.save()
        messages.success(request, "Водитель обновлён.")
        return redirect('drivers')
    return redirect('drivers')


@login_required
@permission_required('crm.delete_driver', raise_exception=True)
def delete_driver(request, driver_id):
    driver = Driver.objects.get(id=driver_id)
    driver.delete()
    messages.success(request, "Водитель удалён.")
    return redirect('drivers')
