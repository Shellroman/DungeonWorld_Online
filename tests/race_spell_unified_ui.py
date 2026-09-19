from pathlib import Path
root=Path(__file__).resolve().parents[1]
js=(root/'static'/'app.js').read_text(encoding='utf-8')
assert 'data-spell-access-enabled' not in js
assert '다른 직업 주문 추가 선택' in js
assert 'cross_class_access' in js
assert '현재 직업 주문 레벨 낮추기' in js
assert '특수(미분류) 주문 자동 습득' in js
assert '이 종족 특성은 무엇을 하나요?' in js
assert '플레이어에게는 이렇게 보입니다' in js
assert '타직업 주문 획득</option>' not in js
assert '주문 레벨 감소</option>' not in js
assert '미분류 주문 습득</option>' not in js
print('unified race spell UI source checks ok')
