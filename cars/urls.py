from django.urls import path

from . import views


urlpatterns = [
    path("", views.dashboard_view, name="dashboard"),
    path("veiculos/", views.vehicle_list_view, name="vehicle_list"),
    path("veiculos/novo/", views.vehicle_create_view, name="vehicle_create"),
    path("veiculos/<int:pk>/", views.vehicle_detail_view, name="vehicle_detail"),
    path("veiculos/<int:pk>/editar/", views.vehicle_update_view, name="vehicle_update"),
    path("veiculos/<int:pk>/excluir/", views.vehicle_delete_view, name="vehicle_delete"),
    path("imagens/<int:pk>/excluir/", views.vehicle_image_delete_view, name="image_delete"),
    path("imagens/<int:pk>/capa/", views.vehicle_image_cover_view, name="image_cover"),
    path("clientes/", views.customer_list_view, name="customer_list"),
    path("clientes/novo/", views.customer_create_view, name="customer_create"),
    path("clientes/<int:pk>/", views.customer_detail_view, name="customer_detail"),
    path("clientes/<int:pk>/editar/", views.customer_update_view, name="customer_update"),
    path("clientes/<int:pk>/excluir/", views.customer_delete_view, name="customer_delete"),
    path("vendas/", views.sale_list_view, name="sale_list"),
    path("vendas/nova/", views.sale_create_view, name="sale_create"),
    path("vendas/<int:pk>/", views.sale_detail_view, name="sale_detail"),
    path("vendas/<int:pk>/editar/", views.sale_update_view, name="sale_update"),
    path("vendas/<int:pk>/cancelar/", views.sale_cancel_view, name="sale_cancel"),
    path("relatorios/", views.reports_view, name="reports"),
    path("relatorios/vendas.csv", views.export_sales_csv_view, name="export_sales_csv"),
    path("relatorios/veiculos.csv", views.export_vehicles_csv_view, name="export_vehicles_csv"),
    path("anuncios/", views.legacy_auto_redirect, name="auto_list"),
    path("new-auto/", views.legacy_auto_redirect, name="new_auto"),
    path("new-car/", views.legacy_auto_redirect, name="new_car"),
    path("new-bike/", views.legacy_auto_redirect, name="new_bike"),
]
