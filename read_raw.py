with open('outputs/flagged-08-05-2026.txt', 'r', encoding='utf-8') as f:
    for line in f:
        if 'RAW ROW' in line:
            print(line.strip())
