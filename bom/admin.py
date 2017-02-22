from django.contrib import admin
from .models import Part, PartClass, Subpart

class SubpartInline(admin.TabularInline):
    model = Subpart
    fk_name = 'assembly_part'
    raw_id_fields = ('assembly_subpart', )
    readonly_fields = ('get_full_atlas_part_number', )

    def get_full_atlas_part_number(self, obj):
        return obj.assembly_subpart.atlas_part_number()
    get_full_atlas_part_number.short_description = 'PartNumber'

class PartClassAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'comment', )

class PartAdmin(admin.ModelAdmin):
    ordering = ('number_class__code', 'number_item', 'number_variation')
    list_display = ('get_full_atlas_part_number', 'revision', 'description', 'manufacturer', 'manufacturer_part_number', )
    raw_id_fields = ('number_class',)
    inlines = [
        SubpartInline,
    ]

    def get_full_atlas_part_number(self, obj):
        return obj.atlas_part_number()
    get_full_atlas_part_number.short_description = 'PartNumber'
    get_full_atlas_part_number.admin_order_field = 'number_class__atlas_part_number'

admin.site.register(PartClass, PartClassAdmin)
admin.site.register(Part, PartAdmin)