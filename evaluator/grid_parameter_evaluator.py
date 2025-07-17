#!/usr/bin/env python3
"""
网格参数评估器
用于评估不同网格参数组合的合理性，帮助优化扫描效率和成本
"""

import math
import json
from dataclasses import dataclass
from typing import List, Dict, Tuple
import matplotlib.pyplot as plt
import numpy as np

@dataclass
class GridConfig:
    """网格配置参数"""
    spacing_km: float      # 网格间距(公里)
    radius_m: int         # 搜索半径(米)
    level_name: str       # 级别名称
    
    @property
    def radius_km(self) -> float:
        return self.radius_m / 1000.0
    
    @property
    def coverage_overlap_ratio(self) -> float:
        """计算覆盖重叠比例"""
        if self.spacing_km >= self.radius_km * 2:
            return 0.0  # 无重叠
        else:
            # 简化计算：重叠面积比例
            overlap_distance = (self.radius_km * 2) - self.spacing_km
            return overlap_distance / (self.radius_km * 2)

@dataclass
class AreaStats:
    """区域统计信息"""
    total_area_km2: float
    grid_count: int
    coverage_area_km2: float
    overlap_ratio: float
    api_calls_estimate: int
    cost_estimate: float

class GridParameterEvaluator:
    """网格参数评估器"""
    
    def __init__(self, api_cost_per_call: float = 0.032):
        self.api_cost_per_call = api_cost_per_call
        
    def calculate_grid_stats(self, config: GridConfig, target_area_km2: float) -> AreaStats:
        """计算网格统计信息"""
        
        # 假设目标区域是圆形，计算半径
        area_radius_km = math.sqrt(target_area_km2 / math.pi)
        
        # 计算需要的网格点数量（简化为正方形网格）
        grid_diameter = area_radius_km * 2
        grids_per_side = math.ceil(grid_diameter / config.spacing_km)
        total_grids = grids_per_side ** 2
        
        # 计算实际覆盖面积
        single_grid_area = math.pi * (config.radius_km ** 2)
        total_coverage_area = total_grids * single_grid_area
        
        # 计算重叠比例
        overlap_ratio = config.coverage_overlap_ratio
        
        # 估算API调用次数和成本
        api_calls = total_grids
        cost = api_calls * self.api_cost_per_call
        
        return AreaStats(
            total_area_km2=target_area_km2,
            grid_count=total_grids,
            coverage_area_km2=total_coverage_area,
            overlap_ratio=overlap_ratio,
            api_calls_estimate=api_calls,
            cost_estimate=cost
        )
    
    def evaluate_config_set(self, configs: List[GridConfig], target_area_km2: float) -> Dict[str, AreaStats]:
        """评估一组配置参数"""
        results = {}
        
        for config in configs:
            stats = self.calculate_grid_stats(config, target_area_km2)
            results[config.level_name] = stats
            
        return results
    
    def find_optimal_spacing(self, radius_m: int, target_area_km2: float, 
                           max_overlap_ratio: float = 0.3) -> List[Tuple[float, AreaStats]]:
        """寻找最优网格间距"""
        radius_km = radius_m / 1000.0
        optimal_configs = []
        
        # 测试不同的间距比例
        spacing_ratios = np.arange(0.5, 2.0, 0.1)  # 从0.5倍半径到2倍半径
        
        for ratio in spacing_ratios:
            spacing_km = radius_km * ratio
            config = GridConfig(
                spacing_km=spacing_km,
                radius_m=radius_m,
                level_name=f"spacing_{ratio:.1f}x_radius"
            )
            
            stats = self.calculate_grid_stats(config, target_area_km2)
            
            # 只保留重叠比例合理的配置
            if stats.overlap_ratio <= max_overlap_ratio:
                optimal_configs.append((ratio, stats))
        
        # 按成本排序
        optimal_configs.sort(key=lambda x: x[1].cost_estimate)
        return optimal_configs
    
    def compare_three_stage_configs(self, target_area_km2: float, 
                                  hotspot_ratio: float = 0.2,
                                  extreme_ratio: float = 0.1) -> Dict[str, any]:
        """比较三阶段扫描配置的效果"""
        
        # 默认配置
        default_configs = [
            GridConfig(7.0, 5000, "宏观扫描"),
            GridConfig(1.4, 1000, "精细扫描"), 
            GridConfig(0.7, 500, "增强扫描")
        ]
        
        # 计算各阶段统计
        macro_stats = self.calculate_grid_stats(default_configs[0], target_area_km2)
        
        # 精细扫描只在热点区域执行
        hotspot_area = target_area_km2 * hotspot_ratio
        fine_stats = self.calculate_grid_stats(default_configs[1], hotspot_area)
        
        # 增强扫描只在极端密度区域执行
        extreme_area = hotspot_area * extreme_ratio
        enhanced_stats = self.calculate_grid_stats(default_configs[2], extreme_area)
        
        # 计算总成本
        total_cost = macro_stats.cost_estimate + fine_stats.cost_estimate + enhanced_stats.cost_estimate
        total_api_calls = macro_stats.api_calls_estimate + fine_stats.api_calls_estimate + enhanced_stats.api_calls_estimate
        
        return {
            "stages": {
                "macro": macro_stats,
                "fine": fine_stats, 
                "enhanced": enhanced_stats
            },
            "total_cost": total_cost,
            "total_api_calls": total_api_calls,
            "cost_breakdown": {
                "macro_percentage": (macro_stats.cost_estimate / total_cost) * 100,
                "fine_percentage": (fine_stats.cost_estimate / total_cost) * 100,
                "enhanced_percentage": (enhanced_stats.cost_estimate / total_cost) * 100
            }
        }
    
    def generate_evaluation_report(self, target_area_km2: float, area_name: str = "目标区域") -> str:
        """生成评估报告"""
        
        print(f"\n=== 网格参数评估报告 - {area_name} ===")
        print(f"目标区域面积: {target_area_km2:.1f} 平方公里")
        
        # 1. 三阶段配置分析
        print(f"\n1. 三阶段扫描配置分析:")
        three_stage_result = self.compare_three_stage_configs(target_area_km2)
        
        for stage_name, stats in three_stage_result["stages"].items():
            print(f"  {stage_name}:")
            print(f"    网格数量: {stats.grid_count}")
            print(f"    API调用: {stats.api_calls_estimate}")
            print(f"    成本: ${stats.cost_estimate:.2f}")
            print(f"    重叠比例: {stats.overlap_ratio:.1%}")
        
        print(f"\n  总计:")
        print(f"    总API调用: {three_stage_result['total_api_calls']}")
        print(f"    总成本: ${three_stage_result['total_cost']:.2f}")
        
        # 2. 网格间距优化建议
        print(f"\n2. 网格间距优化建议:")
        
        # 为每个级别找最优间距
        radii = [5000, 1000, 500]
        level_names = ["宏观", "精细", "增强"]
        
        for radius, level_name in zip(radii, level_names):
            print(f"\n  {level_name}扫描 (半径{radius}米):")
            optimal_configs = self.find_optimal_spacing(radius, target_area_km2)
            
            if optimal_configs:
                # 显示前3个最优配置
                for i, (ratio, stats) in enumerate(optimal_configs[:3]):
                    spacing_km = (radius/1000) * ratio
                    print(f"    选项{i+1}: 间距{spacing_km:.1f}km (半径{ratio:.1f}倍)")
                    print(f"      网格数: {stats.grid_count}, 成本: ${stats.cost_estimate:.2f}, 重叠: {stats.overlap_ratio:.1%}")
        
        # 3. 参数敏感性分析
        print(f"\n3. 参数敏感性分析:")
        self._analyze_parameter_sensitivity(target_area_km2)
        
        return "报告生成完成"
    
    def _analyze_parameter_sensitivity(self, target_area_km2: float):
        """分析参数敏感性"""
        
        base_config = GridConfig(7.0, 5000, "基准配置")
        base_stats = self.calculate_grid_stats(base_config, target_area_km2)
        
        print(f"  基准配置 (间距7km, 半径5km): {base_stats.api_calls_estimate}次调用, ${base_stats.cost_estimate:.2f}")
        
        # 测试间距变化的影响
        spacing_variations = [5.0, 6.0, 8.0, 9.0]
        print(f"  间距变化影响:")
        for spacing in spacing_variations:
            config = GridConfig(spacing, 5000, f"间距{spacing}km")
            stats = self.calculate_grid_stats(config, target_area_km2)
            change_ratio = (stats.cost_estimate - base_stats.cost_estimate) / base_stats.cost_estimate
            print(f"    间距{spacing}km: {stats.api_calls_estimate}次调用, ${stats.cost_estimate:.2f} ({change_ratio:+.1%})")
        
        # 测试半径变化的影响
        radius_variations = [4000, 4500, 5500, 6000]
        print(f"  半径变化影响:")
        for radius in radius_variations:
            config = GridConfig(7.0, radius, f"半径{radius}m")
            stats = self.calculate_grid_stats(config, target_area_km2)
            change_ratio = (stats.cost_estimate - base_stats.cost_estimate) / base_stats.cost_estimate
            print(f"    半径{radius}m: {stats.api_calls_estimate}次调用, ${stats.cost_estimate:.2f} ({change_ratio:+.1%})")

def main():
    """主函数 - 运行评估示例"""
    
    evaluator = GridParameterEvaluator()
    
    # 洛杉矶地区评估 (60英里半径 ≈ 29,315平方公里)
    la_area_km2 = 29315
    evaluator.generate_evaluation_report(la_area_km2, "洛杉矶地区(60英里半径)")
    
    # 小范围测试区域评估 (10平方公里)
    test_area_km2 = 10
    evaluator.generate_evaluation_report(test_area_km2, "小范围测试区域")

if __name__ == "__main__":
    main()