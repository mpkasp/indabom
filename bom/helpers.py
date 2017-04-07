from bom.octopart_parts_match import match_part
from bom.models import Part

def create_some_fake_parts:
    pt1 = Part(manufacturer_part_number='GRM1555C1H100JA01D')
    pt2 = Part(manufacturer_part_number='STM32F401CEU6')
    pt3 = Part(manufacturer_part_number='NRF51822')
