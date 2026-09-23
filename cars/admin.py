from django.contrib import admin

from .models import Brands, Customer, Sale, Vehicle, VehicleImage, VehicleType


class VehicleImageInline(admin.TabularInline):
    model = VehicleImage
    extra = 1


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = (
        "model",
        "brand",
        "vehicle_type",
        "model_year",
        "asking_price",
        "status",
        "entry_date",
    )
    list_filter = ("status", "vehicle_type", "brand")
    search_fields = ("model", "brand__name", "license_plate")
    autocomplete_fields = ("brand",)
    inlines = (VehicleImageInline,)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "email", "created_at")
    search_fields = ("name", "phone", "email", "document")


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "vehicle",
        "customer",
        "sale_date",
        "final_price",
        "payment_method",
        "status",
    )
    list_filter = ("status", "payment_method", "sale_date")
    search_fields = ("vehicle__model", "vehicle__brand__name", "customer__name")
    autocomplete_fields = ("vehicle", "customer")


@admin.register(VehicleType)
class VehicleTypeAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Brands)
class BrandsAdmin(admin.ModelAdmin):
    list_display = ("name", "vehicle_types_display")
    search_fields = ("name",)
    filter_horizontal = ("vehicle_types",)

    @admin.display(description="Tipos")
    def vehicle_types_display(self, brand):
        return ", ".join(vehicle_type.name for vehicle_type in brand.vehicle_types.all())


@admin.register(VehicleImage)
class VehicleImageAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "photo", "is_cover", "uploaded_at")
    list_filter = ("is_cover",)
