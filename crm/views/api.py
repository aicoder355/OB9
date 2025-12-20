from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json

from ..models import Client, Order, Container, Driver
from ..serializers import ClientSerializer, OrderSerializer, ContainerSerializer, DriverSerializer, RegionSerializer


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated]


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]


class ContainerViewSet(viewsets.ModelViewSet):
    queryset = Container.objects.all()
    serializer_class = ContainerSerializer
    permission_classes = [IsAuthenticated]


class DriverViewSet(viewsets.ModelViewSet):
    queryset = Driver.objects.all()
    serializer_class = DriverSerializer
    permission_classes = [IsAuthenticated]


class RegionViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.none()
    serializer_class = RegionSerializer
    permission_classes = [IsAuthenticated]


@csrf_exempt
def api_update_order(request, order_id):
    if request.method == 'PATCH':
        data = json.loads(request.body)
        try:
            order = Order.objects.get(id=order_id)
            driver = getattr(request.user, 'driver_profile', None)
            if request.user.is_authenticated and driver and order.driver == driver:
                if 'status' in data:
                    order.status = data['status']
                if 'driver_comment' in data:
                    order.driver_comment = data['driver_comment']
                if 'return_quantity' in data and data.get('status') == 'returned':
                    container = Container.objects.filter(product=order.product, client=order.client, is_at_client=True).first()
                    if container:
                        container.is_at_client = False
                        container.client = None
                        container.save()
                        warehouse_container = Container.objects.filter(product=order.product, is_at_client=False).first()
                        if warehouse_container:
                            warehouse_container.quantity += data['return_quantity']
                            warehouse_container.save()
                        else:
                            Container.objects.create(product=order.product, quantity=data['return_quantity'], is_at_client=False)
                order.save()
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'error': 'Нет прав'}, status=403)
        except Order.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Заказ не найден'}, status=404)
    return JsonResponse({'success': False, 'error': 'Метод не поддерживается'}, status=405)
