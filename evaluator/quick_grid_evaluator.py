#!/usr/bin/env python3
"""
快速网格参数评估工具
用于快速评估和优化网格参数，避免浪费API调用
"""

import math
from typing import Dict, List, Tuple

class QuickGridEvaluator:
    """快速网格评估器"""
    
    def __init__(self):
        self.api_cost = 0.032
    
    def evaluate_grid_efficiency(self, spacing_km: float, radius_m: int, 
                                area_km2: float) -> Dict[str, float]:
        """评估单个网格配置的效率"""
        
        radius_km = radius_m / 1000.0
        
        # 计算网格数量 (简化为正方形区域)
        area_side_km = math.sqrt(area_km2)
        grids_per_side = math.ceil(area_side_km / spacing_km)
        total_grids = grids_per_side ** 2
        
        # 计算覆盖效率
        single_coverage_area = math.pi * (radius_km ** 2)
        total_coverage = total_grids * single_coverage_area
        coverage_ratio = min(total_coverage / area_km2, 3.0)  # 限制最大3倍覆盖
        
        # 计算重叠程度
        if spacing_km >= radius_km * 2:
            overlap_ratio = 0.0
        else:
            overlap_ratio = 1 - (spacing_km / (radius_km * 2))
        
        # 计算成本效率
        cost = total_grids * self.api_cost
        cost_per_km2 = cost / area_km2
        
        return {
            "grid_count": total_grids,
            "cost": cost,
            "cost_per_km2": cost_per_km2,
            "coverage_ratio": coverage_ratio,
            "overlap_ratio": overlap_ratio,
            "efficiency_score": self._calculate_efficiency_score(coverage_ratio, overlap_ratio, cost_per_km2)
        }
    
    def _calculate_efficiency_score(self, coverage_ratio: float, overlap_ratio: float, 
                                  cost_per_km2: float) -> float:
        """计算效率评分 (0-100分)"""
        
        # 覆盖率评分 (目标是1.0-1.5倍覆盖)
        if 1.0 <= coverage_ratio <= 1.5:
            coverage_score = 100
        elif coverage_ratio < 1.0:
            coverage_score = coverage_ratio * 100  # 覆盖不足扣分
        else:
            coverage_score = max(0, 100 - (coverage_ratio - 1.5) * 50)  # 过度覆盖扣分
        
        # 重叠率评分 (目标是10-30%重叠)
        if 0.1 <= overlap_ratio <= 0.3:
            overlap_score = 100
        elif overlap_ratio < 0.1:
            overlap_score = 50  # 覆盖不足
        else:
            overlap_score = max(0, 100 - (overlap_ratio - 0.3) * 200)  # 过度重叠扣分
        
        # 成本评分 (基于每平方公里成本)
        if cost_per_km2 <= 0.1:
            cost_score = 100
        else:
            cost_score = max(0, 100 - (cost_per_km2 - 0.1) * 500)
        
        # 综合评分
        return (coverage_score * 0.4 + overlap_score * 0.3 + cost_score * 0.3)
    
    def find_best_spacing(self, radius_m: int, area_km2: float) -> List[Tuple[float, Dict]]:
        """为给定半径找到最佳间距"""
        
        radius_km = radius_m / 1000.0
        results = []
        
        # 测试不同间距 (从0.5倍半径到2倍半径)
        spacing_multipliers = [0.5, 0.7, 0.9, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0]
        
        for multiplier in spacing_multipliers:
            spacing_km = radius_km * multiplier
            result = self.evaluate_grid_efficiency(spacing_km, radius_m, area_km2)
            result["spacing_km"] = spacing_km
            result["spacing_multiplier"] = multiplier
            results.append((result["efficiency_score"], result))
        
        # 按效率评分排序
        results.sort(key=lambda x: x[0], reverse=True)
        return results
    
    def quick_three_stage_evaluation(self, area_km2: float, hotspot_ratio: float = 0.2) -> None:
        """快速评估三阶段扫描配置"""
        
        print(f"\n=== 快速三阶段网格评估 ===")
        print(f"目标区域: {area_km2:.0f} 平方公里")
        print(f"热点区域比例: {hotspot_ratio:.0%}")
        
        stages = [
            ("宏观扫描", 5000, area_km2),
            ("精细扫描", 1000, area_km2 * hotspot_ratio),
            ("增强扫描", 500, area_km2 * hotspot_ratio * 0.1)
        ]
        
        total_cost = 0
        total_grids = 0
        
        for stage_name, radius_m, stage_area in stages:
            print(f"\n{stage_name} (半径{radius_m}米, 区域{stage_area:.1f}km²):")
            
            best_configs = self.find_best_spacing(radius_m, stage_area)
            
            # 显示前3个最佳配置
            for i, (score, config) in enumerate(best_configs[:3]):
                print(f"  选项{i+1}: 间距{config['spacing_km']:.1f}km "
                      f"(半径{config['spacing_multiplier']:.1f}倍)")
                print(f"    网格数: {config['grid_count']}, 成本: ${config['cost']:.2f}")
                print(f"    覆盖率: {config['coverage_ratio']:.1f}倍, "
                      f"重叠率: {config['overlap_ratio']:.1%}")
                print(f"    效率评分: {score:.0f}/100")
                
                if i == 0:  # 记录最佳配置的成本
                    total_cost += config['cost']
                    total_grids += config['grid_count']
        
        print(f"\n=== 总计 (使用最佳配置) ===")
        print(f"总网格数: {total_grids}")
        print(f"总成本: ${total_cost:.2f}")
        print(f"平均成本/km²: ${total_cost/area_km2:.3f}")
    
    def parameter_sensitivity_test(self, base_spacing: float, base_radius: int, 
                                 area_km2: float) -> None:
        """参数敏感性测试"""
        
        print(f"\n=== 参数敏感性分析 ===")
        
        # 基准配置
        base_result = self.evaluate_grid_efficiency(base_spacing, base_radius, area_km2)
        print(f"基准配置: 间距{base_spacing}km, 半径{base_radius}m")
        print(f"  网格数: {base_result['grid_count']}, 成本: ${base_result['cost']:.2f}")
        
        # 测试间距变化
        print(f"\n间距变化影响 (半径固定{base_radius}m):")
        spacing_tests = [base_spacing * 0.8, base_spacing * 0.9, 
                        base_spacing * 1.1, base_spacing * 1.2]
        
        for spacing in spacing_tests:
            result = self.evaluate_grid_efficiency(spacing, base_radius, area_km2)
            cost_change = (result['cost'] - base_result['cost']) / base_result['cost']
            print(f"  间距{spacing:.1f}km: {result['grid_count']}网格, "
                  f"${result['cost']:.2f} ({cost_change:+.1%})")
        
        # 测试半径变化
        print(f"\n半径变化影响 (间距固定{base_spacing}km):")
        radius_tests = [int(base_radius * 0.8), int(base_radius * 0.9),
                       int(base_radius * 1.1), int(base_radius * 1.2)]
        
        for radius in radius_tests:
            result = self.evaluate_grid_efficiency(base_spacing, radius, area_km2)
            coverage_change = result['coverage_ratio'] - base_result['coverage_ratio']
            print(f"  半径{radius}m: 覆盖率{result['coverage_ratio']:.1f}倍 "
                  f"({coverage_change:+.1f}), 重叠{result['overlap_ratio']:.1%}")

def main():
    """主函数"""
    evaluator = QuickGridEvaluator()
    
    print("选择评估模式:")
    print("1. 洛杉矶大区域评估 (29,315 km²)")
    print("2. 小范围测试评估 (100 km²)")
    print("3. 自定义区域评估")
    print("4. 参数敏感性测试")
    
    choice = input("请选择 (1-4): ").strip()
    
    if choice == "1":
        evaluator.quick_three_stage_evaluation(29315, 0.2)
    elif choice == "2":
        evaluator.quick_three_stage_evaluation(100, 0.3)
    elif choice == "3":
        area = float(input("请输入区域面积 (平方公里): "))
        hotspot = float(input("请输入热点区域比例 (0.1-0.5): "))
        evaluator.quick_three_stage_evaluation(area, hotspot)
    elif choice == "4":
        evaluator.parameter_sensitivity_test(7.0, 5000, 1000)
    else:
        print("无效选择")

if __name__ == "__main__":
    main()