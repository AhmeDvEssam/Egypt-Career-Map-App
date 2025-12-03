# Quick Git Update Guide

## بعد أي تعديل في المشروع:

### الأوامر الأساسية:

```bash
# 1. شوف إيه اللي اتعدل
git status

# 2. أضف كل التعديلات
git add .

# 3. اعمل commit
git commit -m "Updated author info in README"

# 4. ارفع على GitHub
git push
```

---

## أمثلة لرسائل الـ Commit:

```bash
# لما تعدل في الكود
git commit -m "Fixed KPI calculation bug"

# لما تضيف feature جديدة
git commit -m "Added dark mode toggle"

# لما تعدل في التصميم
git commit -m "Improved responsive design for mobile"

# لما تحدث الـ README
git commit -m "Updated documentation"

# لما تصلح أخطاء
git commit -m "Fixed chart rendering issue"
```

---

## سيناريوهات مختلفة:

### 1. عدلت ملف واحد بس:
```bash
git add README.md
git commit -m "Updated author information"
git push
```

### 2. عدلت ملفات كتير:
```bash
git add .
git commit -m "Multiple improvements: UI fixes and performance"
git push
```

### 3. عاوز تشوف إيه اللي اتعدل قبل ما ترفع:
```bash
git status          # شوف الملفات المعدلة
git diff            # شوف التعديلات بالتفصيل
git add .
git commit -m "Your message"
git push
```

---

## لو حد تاني عدل في المشروع:

```bash
# اسحب آخر تحديثات من GitHub
git pull

# بعدين اعمل تعديلاتك
# ... edit files ...

# ارفع تعديلاتك
git add .
git commit -m "Your changes"
git push
```

---

## أوامر مفيدة:

```bash
# شوف آخر commits
git log --oneline

# تراجع عن آخر commit (لو غلطت)
git reset --soft HEAD~1

# شوف الفروق بين ملف معين
git diff README.md

# شوف حالة المشروع
git status
```

---

## ⚠️ ملاحظات مهمة:

1. **دايماً اعمل `git pull` الأول** لو بتشتغل من أكتر من جهاز
2. **الـ commit message** لازم يكون واضح ويوصف التعديل
3. **متنساش `git add .`** قبل الـ commit
4. **لو في conflict** هيطلب منك تحله قبل الـ push

---

## 🚀 Workflow السريع:

```bash
# كل يوم قبل ما تبدأ شغل
git pull

# بعد ما تخلص شغلك
git add .
git commit -m "Description of work done"
git push

# كرر العملية دي كل ما تعمل تعديل مهم
```
