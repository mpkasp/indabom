from django.contrib import admin
from .models import *

class SubpartInline(admin.TabularInline):
    model = Subpart
    fk_name = 'assembly_part'
    raw_id_fields = ('assembly_subpart', )
    readonly_fields = ('get_full_part_number', )

    def get_full_part_number(self, obj):
        return obj.assembly_subpart.full_part_number()
    get_full_part_number.short_description = 'PartNumber'

class SellerAdmin(admin.ModelAdmin):
    list_display = ('name', )

class SellerPartAdmin(admin.ModelAdmin):
    list_display = ('part', 'seller', 'minimum_order_quantity', 'minimum_pack_quantity', 'unit_cost', 'lead_time_days')

class SellerPartAdminInline(admin.TabularInline):
    model = SellerPart
    raw_id_fields = ('seller', 'part', )

class PartClassAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'comment', )

class PartAdmin(admin.ModelAdmin):
    ordering = ('number_class__code', 'number_item', 'number_variation')
    readonly_fields = ('get_full_part_number', )
    list_display = ('get_full_part_number', 'revision', 'description', 'manufacturer_name', 'manufacturer_part_number', )
    raw_id_fields = ('number_class',)
    inlines = [
        SubpartInline,
        SellerPartAdminInline,
    ]

    def get_full_part_number(self, obj):
        return obj.full_part_number()
    get_full_part_number.short_description = 'PartNumber'
    get_full_part_number.admin_order_field = 'number_class__part_number'

class ManufacturerAdmin(admin.ModelAdmin):
    list_display = ('name', )

class PartFileAdmin(admin.ModelAdmin):
    list_display = ('file', 'upload_date', 'get_full_part_number')
    raw_id_fields = ('part',)

    def get_full_part_number(self, obj):
        return obj.part.full_part_number()
    get_full_part_number.short_description = 'PartNumber'
    
admin.site.register(Seller, SellerAdmin)
admin.site.register(SellerPart, SellerPartAdmin)
admin.site.register(PartClass, PartClassAdmin)
admin.site.register(Part, PartAdmin)
admin.site.register(Manufacturer, ManufacturerAdmin)
admin.site.register(PartFile, PartFileAdmin)
