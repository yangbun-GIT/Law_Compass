import os

def merge_code(root_dir, output_file):
    with open(output_file, 'w', encoding='utf-8') as outfile:
        for root, dirs, files in os.walk(root_dir):
            # 제외할 폴더 설정 (예: .git, node_modules 등)
            dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '__pycache__']]
            for file in files:
                if file.endswith(('.py', '.js', '.ts', '.java', '.c', '.cpp', '.h')): # 필요한 확장자 추가
                    file_path = os.path.join(root, file)
                    outfile.write(f"\n\n{'='*20}\nFile: {file_path}\n{'='*20}\n\n")
                    try:
                        with open(file_path, 'r', encoding='utf-8') as infile:
                            outfile.write(infile.read())
                    except:
                        outfile.write("// 파일 읽기 실패\n")

merge_code('./', 'project_combined.txt')