#!/usr/bin/env python3
import os
from PIL import Image
import math

def next_power_of_two(n):
    return 2 ** math.ceil(math.log2(n))

def process_image(input_path, output_path):
    # 打开图片
    img = Image.open(input_path)
    
    # 获取原始尺寸
    width, height = img.size
    
    # 计算新的尺寸（2的幂次方）
    new_width = next_power_of_two(width)
    new_height = next_power_of_two(height)
    
    # 如果尺寸已经是2的幂次方，则跳过
    if new_width == width and new_height == height:
        print(f"Skipping {input_path} - already power of two")
        return
    
    # 创建新的透明画布
    new_img = Image.new('RGBA', (new_width, new_height), (0, 0, 0, 0))
    
    # 将原图粘贴到左上角
    new_img.paste(img, (0, 0))
    
    # 保存新图片
    new_img.save(output_path)
    print(f"Processed {input_path} -> {output_path} ({width}x{height} -> {new_width}x{new_height})")

def process_directory(input_dir, output_dir):
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 遍历所有文件
    for root, dirs, files in os.walk(input_dir):
        # 计算相对路径
        rel_path = os.path.relpath(root, input_dir)
        if rel_path == '.':
            rel_path = ''
            
        # 创建对应的输出子目录
        output_subdir = os.path.join(output_dir, rel_path)
        os.makedirs(output_subdir, exist_ok=True)
        
        # 处理所有PNG文件
        for file in files:
            if file.lower().endswith('.png'):
                input_path = os.path.join(root, file)
                output_path = os.path.join(output_subdir, file)
                process_image(input_path, output_path)

def main():
    # 处理1x和2x目录
    base_dir = 'resources/textures'
    for scale in ['1x', '2x']:
        input_dir = os.path.join(base_dir, scale)
        output_dir = os.path.join(base_dir, f"{scale}_power_of_two")
        print(f"\nProcessing {scale} directory...")
        process_directory(input_dir, output_dir)

if __name__ == '__main__':
    main() 