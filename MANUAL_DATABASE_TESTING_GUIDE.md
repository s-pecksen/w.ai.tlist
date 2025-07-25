# Manual Database Testing Guide for Supabase

This guide helps you verify all database functionality works correctly through the web interface.

## 🚀 Quick Automated Test

**Run this first to test everything automatically:**

```bash
python test_supabase_functionality.py
```

This comprehensive script tests all database operations, error handling, and performance.

---

## 🖱️ Manual UI Testing Checklist

### 1. User Account Testing

#### ✅ Registration & Authentication
- [ ] **Register new account** with unique email
- [ ] **Complete Stripe checkout** (free trial)
- [ ] **Login with new account**
- [ ] **Logout and login again**
- [ ] **Try invalid login credentials** (should fail gracefully)

#### ✅ Settings Management
- [ ] Go to **Settings** page
- [ ] **Update clinic name**
- [ ] **Update user name**
- [ ] **Change password**
- [ ] **Verify changes persist** after logout/login

### 2. Provider Management Testing

#### ✅ Provider CRUD Operations
- [ ] Navigate to **"Manage Providers"**
- [ ] **Add new provider** (First Name + Last Initial)
- [ ] **Verify provider appears** in the list
- [ ] **Add multiple providers** (3-5 different ones)
- [ ] **Remove a provider**
- [ ] **Check providers appear** in patient/slot forms

### 3. Appointment Types Testing

#### ✅ Appointment Type CRUD Operations
- [ ] Navigate to **"Manage Appt Types"**
- [ ] **Add new appointment type** with multiple durations
- [ ] **Edit existing appointment type**
- [ ] **Remove an appointment type**
- [ ] **Verify types appear** in patient forms

### 4. Patient Management Testing

#### ✅ Single Patient Operations
- [ ] Go to **Dashboard** (main page)
- [ ] **Add new patient** with complete information:
  - Name, phone, email
  - Reason for visit
  - Urgency level
  - Appointment type
  - Duration
  - Preferred provider
  - Availability schedule
- [ ] **Verify patient appears** in the list
- [ ] **Edit patient** information
- [ ] **Remove patient**

#### ✅ Bulk Patient Operations
- [ ] **Upload CSV file** with multiple patients
- [ ] **Verify all patients imported** correctly
- [ ] **Check data integrity** (names, phones, etc.)

### 5. Slot/Appointment Management Testing

#### ✅ Slot CRUD Operations
- [ ] Navigate to **"Open Slots"**
- [ ] **Add cancelled appointment** (open slot):
  - Date and time
  - Duration
  - Provider
  - Appointment type
  - Reason for cancellation
- [ ] **Verify slot appears** in list
- [ ] **Edit slot details**
- [ ] **Remove slot**

#### ✅ Matching System Testing
- [ ] **Create both patients and slots** that match:
  - Same appointment type
  - Compatible duration
  - Same provider
  - Overlapping availability
- [ ] **Find matches** for a slot
- [ ] **Propose match** between patient and slot
- [ ] **Confirm booking** (should remove both patient and slot)
- [ ] **Test cancelling proposal**

### 6. Data Persistence Testing

#### ✅ Session & Database Persistence
- [ ] **Add various data** (patients, providers, slots)
- [ ] **Logout completely**
- [ ] **Close browser**
- [ ] **Reopen and login**
- [ ] **Verify all data still exists**

#### ✅ Cross-User Data Isolation
- [ ] **Register second test account**
- [ ] **Add data to second account**
- [ ] **Switch between accounts**
- [ ] **Verify each account only sees their own data**

### 7. Error Handling Testing

#### ✅ Form Validation
- [ ] **Submit empty forms** (should show validation errors)
- [ ] **Submit invalid email formats**
- [ ] **Submit duplicate data** (if constraints exist)
- [ ] **Test all required field validations**

#### ✅ Network & Database Errors
- [ ] **Disconnect internet briefly** during operations
- [ ] **Test with slow connection**
- [ ] **Verify graceful error messages**

### 8. Performance Testing

#### ✅ Large Dataset Handling
- [ ] **Import large CSV** (50+ patients)
- [ ] **Add many providers** (10+ providers)
- [ ] **Create many slots** (20+ slots)
- [ ] **Test search/filter performance**
- [ ] **Verify UI remains responsive**

### 9. Complex Workflow Testing

#### ✅ Complete Patient Journey
1. **Register new account** → Stripe checkout → Login
2. **Setup providers and appointment types**
3. **Add patients** via form and CSV
4. **Add cancelled slots**
5. **Find and confirm matches**
6. **Verify data integrity throughout**

#### ✅ Multi-Session Testing
- [ ] **Open multiple browser tabs**
- [ ] **Perform operations in different tabs**
- [ ] **Verify data synchronization**

---

## 🔧 Troubleshooting Database Issues

### Connection Problems
```bash
# Test database connection directly
python -c "
from src.config import Config
import psycopg2
try:
    conn = psycopg2.connect(Config.DATABASE_URL)
    print('✅ Database connection successful')
    conn.close()
except Exception as e:
    print(f'❌ Connection failed: {e}')
"
```

### Performance Issues
- Monitor Supabase dashboard for slow queries
- Check connection pool settings
- Verify indexes on frequently queried fields

### Data Integrity Issues
- Check foreign key constraints
- Verify JSON field formatting
- Test transaction rollbacks

---

## 📊 Success Criteria

**Your database is working correctly if:**

✅ All manual tests pass without errors  
✅ Automated test script completes successfully  
✅ Data persists across sessions  
✅ User data is properly isolated  
✅ Performance is acceptable under load  
✅ Error handling is graceful  
✅ Stripe integration works with database  

---

## 🚨 If Tests Fail

1. **Check Supabase dashboard** for connection issues
2. **Review application logs** for specific errors
3. **Verify environment variables** (.env file)
4. **Test connection parameters** (host, port, credentials)
5. **Check database permissions** in Supabase console

**Need help?** Run the automated test script first - it provides detailed error messages and diagnostics. 