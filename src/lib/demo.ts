// Демо-дані для першого запуску (чекбокс на екрані налаштування). Можна видалити з адмінки/боту.

export const DEMO_SUBJECTS = [
  { key: "alg", kind: "subject", title: "Алгоритми та структури даних", code: "ALG201", instructor: "О. Коваленко", description: "Складність алгоритмів, масиви, списки, дерева, графи та динамічне програмування.", year: 2, term: 1, ects: 5 },
  { key: "db", kind: "subject", title: "Бази даних", code: "DB210", instructor: "І. Мельник", description: "Реляційна модель, SQL, нормалізація, індекси та транзакції.", year: 2, term: 2, ects: 5 },
  { key: "eng", kind: "subject", title: "Англійська мова", code: "ENG101", instructor: "К. Савчук", description: "Академічна лексика та граматика.", year: 1, term: 1, ects: 3 },
  { key: "agents", kind: "course", title: "AI Agents", provider: "Hugging Face", url: "https://huggingface.co/learn", description: "Практичний курс про побудову агентів на основі LLM." },
] as const;

const bigO = `## Головне

- **O(1)** — константний час
- **O(log n)** — бінарний пошук
- **O(n log n)** — ефективні сортування

### Порівняння

| Алгоритм | Складність |
|---|---|
| Лінійний пошук | O(n) |
| Бінарний пошук | O(log n) |
| Хеш-таблиця | O(1) у середньому |

### Перевірка

- [x] Розумію, що таке асимптотика
- [ ] Можу оцінити складність вкладених циклів

Для масиву з $n = 10^6$ елементів бінарний пошук робить приблизно $\\log_2 n \\approx 20$ кроків.

\`\`\`python
def binary_search(a, x):
    lo, hi = 0, len(a) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if a[mid] == x:
            return mid
        lo, hi = (mid + 1, hi) if a[mid] < x else (lo, mid - 1)
    return -1
\`\`\``;

const norm = `## Нормалізація

- **1НФ** — атомарні значення в колонках
- **2НФ** — немає часткових залежностей від ключа
- **3НФ** — немає транзитивних залежностей`;

export const DEMO_LESSONS = [
  { subject: "alg", number: 1, kind: "lecture", title: "Складність алгоритмів та O-нотація", description: "Вступ до асимптотичного аналізу.", summary: bigO, summarySource: "ai", videoUrl: "https://www.youtube.com/watch?v=dQw4w9WgXcQ", heldOn: "2025-09-05", key: "alg1" },
  { subject: "alg", number: 2, kind: "lecture", title: "Масиви та зв'язні списки", summary: "## Масив vs список\n\n- Масив: доступ за індексом **O(1)**, вставка **O(n)**\n- Список: вставка **O(1)** за посиланням, доступ **O(n)**", summarySource: "manual", heldOn: "2025-09-12", key: "alg2" },
  { subject: "alg", number: 1, kind: "practice", title: "Бінарний пошук", description: "Реалізуємо бінарний пошук та розбираємо крайові випадки.", heldOn: "2025-09-14", key: "alg3" },
  { subject: "alg", number: 3, kind: "lecture", title: "Дерева пошуку", summary: "## Бінарні дерева пошуку\n\nДля кожного вузла: **ліве піддерево < вузол < праве піддерево**.", summarySource: "ai", heldOn: "2025-09-19", key: "alg4" },
  { subject: "db", number: 1, kind: "lecture", title: "Реляційна модель", description: "Відношення, ключі, реляційна алгебра.", heldOn: "2026-02-10", key: "db1" },
  { subject: "db", number: 2, kind: "lecture", title: "Нормалізація", summary: norm, summarySource: "manual", heldOn: "2026-02-17", key: "db2" },
  { subject: "db", number: 1, kind: "lab", title: "SQL: JOIN та агрегації", heldOn: "2026-02-20", key: "db3" },
  { subject: "eng", number: 1, kind: "seminar", title: "Academic vocabulary: Unit 1", description: "Слова з першого розділу. Пройди міні-тест нижче.", key: "eng1" },
  { subject: "agents", number: 1, kind: "video", title: "Що таке агент?", description: "Цикл «думка — дія — спостереження».", key: "ag1" },
  { subject: "agents", number: 2, kind: "reading", title: "Інструменти та виклик функцій", key: "ag2" },
] as const;

const quizHtml = `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><style>
body{font-family:system-ui,sans-serif;max-width:560px;margin:24px auto;padding:0 16px;color:#222}
h2{font-size:18px}.q{margin:18px 0;padding:14px;border:1px solid #ddd;border-radius:10px}
label{display:block;margin:6px 0;cursor:pointer}button{padding:8px 14px;border:0;border-radius:8px;background:#222;color:#fff;cursor:pointer}
.ok{color:#15803d}.bad{color:#b91c1c}
</style></head><body>
<h2>Academic vocabulary — quick quiz</h2>
<div class="q" data-a="b"><b>1. "Hypothesis" means…</b>
<label><input type="radio" name="q1" value="a"> a final result</label>
<label><input type="radio" name="q1" value="b"> a proposed explanation</label>
<label><input type="radio" name="q1" value="c"> a type of graph</label></div>
<div class="q" data-a="c"><b>2. Choose the synonym of "to analyse":</b>
<label><input type="radio" name="q2" value="a"> to ignore</label>
<label><input type="radio" name="q2" value="b"> to copy</label>
<label><input type="radio" name="q2" value="c"> to examine</label></div>
<button onclick="check()">Check</button> <span id="r"></span>
<script>
function check(){var s=0,qs=document.querySelectorAll('.q');
qs.forEach(function(q){var v=q.querySelector('input:checked');var ok=v&&v.value===q.dataset.a;if(ok)s++;
q.style.borderColor=ok?'#16a34a':'#dc2626'});
var r=document.getElementById('r');r.textContent=s+' / '+qs.length;r.className=s===qs.length?'ok':'bad'}
</script></body></html>`;

const pyTask = `# Завдання: бінарний пошук
# Допиши функцію binary_search(a, x): поверни індекс x у відсортованому списку a або -1.

def binary_search(a, x):
    # TODO: твій код
    return -1


# Перевірка
tests = [
    (([1, 3, 5, 7, 9], 7), 3),
    (([1, 3, 5, 7, 9], 1), 0),
    (([1, 3, 5, 7, 9], 4), -1),
    (([], 1), -1),
]
for (args, expected) in tests:
    got = binary_search(*args)
    print("OK " if got == expected else "FAIL", args, "->", got, "(очікувалось", expected, ")")
`;

const mdTask = `# Нормалізація: розбір таблиці

Дано таблицю **Замовлення**:

| order_id | customer | phones | item | price |
|---|---|---|---|---|
| 1 | Іра | 050, 067 | Книга | 200 |
| 2 | Макс | 093 | Ручка | 20 |

## Що зробити

1. Поясни, чому таблиця **не в 1НФ**.
2. Розбий її на таблиці, що відповідають **3НФ**.
3. Напиши \`CREATE TABLE\` для кожної.

\`\`\`sql
-- твоя відповідь тут
\`\`\`

- [ ] Пункт 1
- [ ] Пункт 2
- [ ] Пункт 3
`;

export const DEMO_TASKS = [
  { lesson: "eng1", title: "Vocabulary quiz (Unit 1)", kind: "html", content: quizHtml, fileName: "unit1_quiz.html" },
  { lesson: "alg3", title: "Реалізація binary_search", kind: "python", content: pyTask, fileName: "binary_search.py" },
  { lesson: "db2", title: "Нормалізація таблиці замовлень", kind: "markdown", content: mdTask, fileName: "normalization.md" },
] as const;
