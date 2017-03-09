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

class DistributorAdmin(admin.ModelAdmin):
    list_display = ('name', )

class DistributorPartAdmin(admin.ModelAdmin):
    list_display = ('part', 'distributor', 'minimum_order_quantity', 'minimum_pack_quantity', 'unit_cost', 'lead_time_days')

class DistributorPartAdminInline(admin.TabularInline):
    model = DistributorPart
    raw_id_fields = ('distributor', 'part', )

class PartClassAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'comment', )

class PartAdmin(admin.ModelAdmin):
    ordering = ('number_class__code', 'number_item', 'number_variation')
    readonly_fields = ('get_full_part_number', )
    list_display = ('get_full_part_number', 'revision', 'description', 'manufacturer', 'manufacturer_part_number', )
    raw_id_fields = ('number_class',)
    inlines = [
        SubpartInline,
        DistributorPartAdminInline,
    ]

    def get_full_part_number(self, obj):
        return obj.full_part_number()
    get_full_part_number.short_description = 'PartNumber'
    get_full_part_number.admin_order_field = 'number_class__part_number'

admin.site.register(Distributor, DistributorAdmin)
admin.site.register(DistributorPart, DistributorPartAdmin)
admin.site.register(PartClass, PartClassAdmin)
admin.site.register(Part, PartAdmin)