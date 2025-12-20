from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from django.core.paginator import Paginator
from django.contrib import messages
from django.db.models import Q, Sum, Count, Max
from django.utils import timezone

from ..models import Client, Region, ClientCategory, Container


@login_required
def clients(request):
    search_query = request.GET.get('search', '')
    
    clients_qs = Client.objects.select_related('region', 'category').all()
    if search_query:
        clients_qs = clients_qs.filter(
            Q(name__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(company_name__icontains=search_query) |
            Q(tax_number__icontains=search_query)
        )

    clients_qs = clients_qs.annotate(
        orders_count=Count('order'),
        total_orders_volume=Sum('order__quantity'),
        last_order_date=Max('order__order_date')
    ).order_by('-last_order_date', 'name')

    paginator = Paginator(clients_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'clients.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'regions': Region.objects.all(),
        'categories': ClientCategory.objects.all(),
        'can_add_client': request.user.has_perm('crm.add_client'),
        'can_change_client': request.user.has_perm('crm.change_client'),
        'can_delete_client': request.user.has_perm('crm.delete_client'),
    })


@login_required
@permission_required('crm.add_client', raise_exception=True)
def create_client(request):
    if request.method == 'POST':
        client_type = request.POST.get('client_type', 'individual')
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        email = request.POST.get('email', '')
        address = request.POST.get('address')
        apartment = request.POST.get('apartment', '')
        floor = request.POST.get('floor')
        entrance = request.POST.get('entrance', '')
        region_id = request.POST.get('region')
        notes = request.POST.get('notes', '')
        company_name = request.POST.get('company_name', '')
        tax_number = request.POST.get('tax_number', '')
        contact_person = request.POST.get('contact_person', '')

        try:
            Client.objects.create(
                client_type=client_type,
                name=name,
                phone=phone,
                email=email,
                address=address,
                apartment=apartment,
                floor=floor if floor else None,
                entrance=entrance,
                region_id=region_id if region_id else None,
                notes=notes,
                company_name=company_name if client_type == 'business' else '',
                tax_number=tax_number if client_type == 'business' else '',
                contact_person=contact_person if client_type == 'business' else ''
            )
            messages.success(request, "Клиент создан успешно.")
        except Exception as e:
            messages.error(request, f"Ошибка при создании клиента: {str(e)}")
        
        return redirect('clients')
    return redirect('clients')


@login_required
@permission_required('crm.change_client', raise_exception=True)
def edit_client(request):
    if request.method == 'POST':
        client = get_object_or_404(Client, id=request.POST.get('client_id'))
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        client_type = request.POST.get('client_type', 'individual')

        if not name:
            messages.error(request, "Имя клиента обязательно для заполнения")
            return redirect('clients')
        if not phone:
            messages.error(request, "Номер телефона обязателен для заполнения")
            return redirect('clients')

        if client_type == 'business':
            company_name = request.POST.get('company_name', '').strip()
            tax_number = request.POST.get('tax_number', '').strip()
            if not company_name:
                messages.error(request, "Название компании обязательно для юридического лица")
                return redirect('clients')
            if not tax_number:
                messages.error(request, "ИНН обязателен для юридического лица")
                return redirect('clients')

        client.client_type = client_type
        client.name = name
        client.phone = phone
        client.email = request.POST.get('email', '').strip()
        client.address = request.POST.get('address', '').strip()
        client.apartment = request.POST.get('apartment', '').strip()
        client.floor = request.POST.get('floor') if request.POST.get('floor') else None
        client.entrance = request.POST.get('entrance', '').strip()
        client.region_id = request.POST.get('region') if request.POST.get('region') else None
        client.notes = request.POST.get('notes', '').strip()

        if client_type == 'business':
            client.company_name = company_name
            client.tax_number = tax_number
            client.contact_person = request.POST.get('contact_person', '').strip()
        else:
            client.company_name = ''
            client.tax_number = ''
            client.contact_person = ''

        try:
            client.save()
            messages.success(request, "Клиент обновлён успешно.")
        except Exception as e:
            messages.error(request, f"Ошибка при обновлении клиента: {str(e)}")
        
        return redirect('clients')
    return redirect('clients')


@login_required
@permission_required('crm.change_client', raise_exception=True)
def attach_client_to_region(request):
    if request.method == 'POST':
        client_id = request.POST.get('client_id')
        region_id = request.POST.get('region')
        
        if not client_id:
            messages.error(request, "Клиент не выбран")
            return redirect('regions')
        if not region_id:
            messages.error(request, "Регион не выбран")
            return redirect('regions')
        try:
            client = Client.objects.get(id=client_id)
            client.region_id = region_id
            client.save()
            messages.success(request, "Клиент успешно прикреплен к региону")
        except Client.DoesNotExist:
            messages.error(request, "Клиент не найден")
        except Exception as e:
            messages.error(request, f"Ошибка при прикреплении клиента к региону: {str(e)}")
        
        return redirect('regions')
    return redirect('regions')


@login_required
@permission_required('crm.delete_client', raise_exception=True)
def delete_client(request, client_id):
    client = Client.objects.get(id=client_id)
    if client.order_set.exists():
        messages.error(request, "Нельзя удалить клиента, у которого есть заказы.")
        return redirect('clients')
    if Container.objects.filter(client=client, is_at_client=True).exists():
        messages.error(request, "Нельзя удалить клиента, у которого есть тара.")
        return redirect('clients')
    client.delete()
    messages.success(request, "Клиент удалён.")
    return redirect('clients')
