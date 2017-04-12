from bom.octopart_parts_match import match_part
from bom.models import Part, PartClass, Distributor, DistributorPart, Subpart

def create_some_fake_part_classes():
    pc1 = PartClass(code=500,name='Wendy',comment='Mechanical Switches')
    pc1.save()

    pc2 = PartClass(code=200,name='Archibald', comment='')
    pc2.save()

    pc3 = PartClass(code=503,name='Ghost',comment='Like Kasper')
    pc3.save()

    return pc1, pc2, pc3


def create_a_fake_subpart(assembly_part, assembly_subpart, count=4):
    sp1 = Subpart(assembly_part=assembly_part, assembly_subpart=assembly_subpart, count=count)
    sp1.save()


def create_some_fake_sellers():
    s1 = Distributor(name='Mouser')
    s1.save()
    
    s2 = Distributor(name='Digi-Key')
    s2.save()

    s3 = Distributor(name='Archibald')
    s3.save()

    return s1, s2, s3


def create_a_fake_seller_part(distributor, part, moq, mpq, unit_cost, lead_time_days):
    sp1 = DistributorPart(distributor=distributor, part=part, minimum_order_quantity=moq, 
                            minimum_pack_quantity=mpq, unit_cost=unit_cost, lead_time_days=lead_time_days)
    sp1.save()

    return sp1


def create_some_fake_parts():
    (pc1, pc2, pc3) = create_some_fake_part_classes()

    pt1 = Part(manufacturer_part_number='STM32F401CEU6', number_class=pc2, number_item='3333', description='Brown dog', revision='1', manufacturer='STMicroelectronics')    
    pt1.save()

    pt2 = Part(manufacturer_part_number='GRM1555C1H100JA01D', number_class=pc1, description='', manufacturer='')
    pt2.save()

    pt3 = Part(manufacturer_part_number='NRF51822', number_class=pc3, description='Friendly ghost', manufacturer='Nordic Semiconductor')
    pt3.save()

    create_a_fake_subpart(pt1, pt2)
    create_a_fake_subpart(pt1, pt3, count=10)

    (s1, s2, s3) = create_some_fake_sellers()

    create_a_fake_seller_part(s1, pt1, moq=None, mpq=None, unit_cost=None, lead_time_days=None)
    create_a_fake_seller_part(s2, pt1, moq=1000, mpq=5000, unit_cost=0.1005, lead_time_days=7)
    create_a_fake_seller_part(s2, pt2, moq=200, mpq=200, unit_cost=0, lead_time_days=47)

    return pt1, pt2, pt3
