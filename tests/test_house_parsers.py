"""房源解析函数单元测试

测试房源路由中的辅助解析函数，确保数据转换正确。
"""

import pytest
from typing import Optional, Tuple

from app.models import Orientation, Decoration
from app.routers.house import (
    parse_orientation,
    parse_decoration,
    parse_floor,
    facilities_list_to_dict,
)


class TestOrientationParser:
    """测试朝向解析函数"""

    def test_parse_orientation_none(self):
        """测试空输入返回None"""
        assert parse_orientation(None) is None
        assert parse_orientation("") is None

    def test_parse_orientation_lowercase(self):
        """测试小写朝向字符串"""
        assert parse_orientation("south") == Orientation.SOUTH
        assert parse_orientation("north") == Orientation.NORTH
        assert parse_orientation("east") == Orientation.EAST
        assert parse_orientation("west") == Orientation.WEST
        assert parse_orientation("southeast") == Orientation.SOUTHEAST
        assert parse_orientation("southwest") == Orientation.SOUTHWEST
        assert parse_orientation("northeast") == Orientation.NORTHEAST
        assert parse_orientation("northwest") == Orientation.NORTHWEST

    def test_parse_orientation_uppercase(self):
        """测试大写朝向字符串"""
        assert parse_orientation("SOUTH") == Orientation.SOUTH
        assert parse_orientation("North") == Orientation.NORTH
        assert parse_orientation("SouthEast") == Orientation.SOUTHEAST

    def test_parse_orientation_enum_value(self):
        """测试直接传入枚举值字符串"""
        assert parse_orientation("SOUTH") == Orientation.SOUTH

    def test_parse_orientation_invalid(self):
        """测试无效朝向返回None"""
        assert parse_orientation("invalid") is None
        assert parse_orientation("123") is None
        assert parse_orientation("bottom") is None


class TestDecorationParser:
    """测试装修程度解析函数"""

    def test_parse_decoration_none(self):
        """测试空输入返回None"""
        assert parse_decoration(None) is None
        assert parse_decoration("") is None

    def test_parse_decoration_bare(self):
        """测试毛坯/简装映射"""
        assert parse_decoration("bare") == Decoration.BARE
        assert parse_decoration("rough") == Decoration.BARE

    def test_parse_decoration_simple(self):
        """测试简装/中装映射"""
        assert parse_decoration("simple") == Decoration.SIMPLE
        assert parse_decoration("standard") == Decoration.SIMPLE

    def test_parse_decoration_fine(self):
        """测试精装映射"""
        assert parse_decoration("fine") == Decoration.FINE

    def test_parse_decoration_luxury(self):
        """测试豪装映射"""
        assert parse_decoration("luxury") == Decoration.LUXURY

    def test_parse_decoration_case_insensitive(self):
        """测试大小写不敏感"""
        assert parse_decoration("SIMPLE") == Decoration.SIMPLE
        assert parse_decoration("Rough") == Decoration.BARE
        assert parse_decoration("Fine") == Decoration.FINE

    def test_parse_decoration_invalid(self):
        """测试无效装修类型返回None"""
        assert parse_decoration("invalid") is None
        assert parse_decoration("unknown") is None


class TestFloorParser:
    """测试楼层解析函数"""

    def test_parse_floor_none(self):
        """测试空输入"""
        assert parse_floor(None) == (None, None)
        assert parse_floor("") == (None, None)

    def test_parse_floor_with_slash(self):
        """测试格式 "当前楼层/总楼层" """
        assert parse_floor("12/28") == (12, 28)
        assert parse_floor("5/10") == (5, 10)
        assert parse_floor("1/1") == (1, 1)

    def test_parse_floor_with_spaces(self):
        """测试带空格的格式"""
        assert parse_floor(" 12 / 28 ") == (12, 28)
        assert parse_floor("5 /10") == (5, 10)

    def test_parse_floor_only_current(self):
        """测试只有当前楼层"""
        assert parse_floor("12") == (12, None)
        assert parse_floor("0") == (0, None)

    def test_parse_floor_invalid_part(self):
        """测试部分无效的情况"""
        assert parse_floor("/28") == (None, 28)
        assert parse_floor("12/") == (12, None)
        assert parse_floor("abc/28") == (None, 28)
        assert parse_floor("12/xyz") == (12, None)

    def test_parse_floor_completely_invalid(self):
        """测试完全无效的输入"""
        assert parse_floor("abc") == (None, None)
        assert parse_floor("abc/def") == (None, None)

    def test_parse_floor_negative(self):
        """测试负数楼层"""
        assert parse_floor("-1/28") == (-1, 28)
        assert parse_floor("1/-1") == (1, -1)


class TestFacilitiesParser:
    """测试设施列表转字典函数"""

    def test_facilities_list_to_dict_none(self):
        """测试空输入"""
        assert facilities_list_to_dict(None) == {}

    def test_facilities_list_to_dict_empty(self):
        """测试空列表"""
        assert facilities_list_to_dict([]) == {}

    def test_facilities_list_to_dict_single(self):
        """测试单个设施"""
        result = facilities_list_to_dict(["wifi"])
        assert result == {"wifi": True}

    def test_facilities_list_to_dict_multiple(self):
        """测试多个设施"""
        result = facilities_list_to_dict(["wifi", "aircon", "heater"])
        assert result == {
            "wifi": True,
            "aircon": True,
            "heater": True,
        }

    def test_facilities_list_to_dict_empty_strings(self):
        """测试包含空字符串的列表"""
        result = facilities_list_to_dict(["wifi", "", None, "aircon"])
        assert result == {
            "wifi": True,
            "aircon": True,
        }

    def test_facilities_list_to_dict_duplicates(self):
        """测试重复的设施"""
        result = facilities_list_to_dict(["wifi", "wifi", "aircon"])
        assert result == {
            "wifi": True,
            "aircon": True,
        }


class TestIntegration:
    """集成测试：模拟发布房源的数据转换流程"""

    def test_full_house_data_parsing(self):
        """测试完整的房源数据解析流程"""
        front_end_data = {
            "title": "精装两居室 近地铁",
            "city": "北京",
            "district": "朝阳区",
            "address": "望京SOHO",
            "price": 5000,
            "area": 80,
            "bedrooms": 2,
            "livingrooms": 1,
            "bathrooms": 1,
            "property_type": "apartment",
            "orientation_str": "south",
            "decoration_str": "fine",
            "floor_str": "12/28",
            "facilities_list": ["wifi", "aircon", "heater"],
        }

        orientation = parse_orientation(front_end_data["orientation_str"])
        decoration = parse_decoration(front_end_data["decoration_str"])
        floor, total_floors = parse_floor(front_end_data["floor_str"])
        facilities = facilities_list_to_dict(front_end_data["facilities_list"])

        assert orientation == Orientation.SOUTH
        assert decoration == Decoration.FINE
        assert floor == 12
        assert total_floors == 28
        assert facilities == {"wifi": True, "aircon": True, "heater": True}

    def test_edge_cases_parsing(self):
        """测试边界情况"""
        test_cases = [
            ({"orientation": None, "decoration": None, "floor": ""},
             (None, None, None, None, {})),
            ({"orientation": "invalid", "decoration": "unknown", "floor": "abc"},
             (None, None, None, None, {})),
        ]

        for data, expected in test_cases:
            orientation = parse_orientation(data.get("orientation"))
            decoration = parse_decoration(data.get("decoration"))
            floor, total_floors = parse_floor(data.get("floor"))
            assert (orientation, decoration, floor, total_floors, {}) == expected
