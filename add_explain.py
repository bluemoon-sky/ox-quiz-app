import re

# 원본 파일
input_file = "ox문제.txt"
# 설명 템플릿이 붙은 새 파일
output_file = "ox문제_with_explain.txt"

# 문제 패턴 (마지막 (O) 또는 (X) 찾기)
pattern = re.compile(r"(.*?\(\s*[OX]\s*\))")

with open(input_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    line = line.strip()
    if not line:
        continue
    m = pattern.match(line)
    if m:
        # 이미 설명이 들어간 문제는 건너뛰기
        if "[설명:" in line or "[오답:" in line:
            new_lines.append(line)
        else:
            new_lines.append(f"{line} [설명: ] [오답: ]")
    else:
        new_lines.append(line)

with open(output_file, "w", encoding="utf-8") as f:
    f.write("\n".join(new_lines))

print(f"완성된 파일: {output_file}")
