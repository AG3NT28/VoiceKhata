import './styles/voicekhata.css';
import './styles/features.css';
import './styles/theme-earth.css';
import {
  ensureAuth,
  getState,
  sendAudio,
  speakText,
  listCustomers,
  createCustomer,
  updateCustomer,
  archiveCustomer,
  getCustomerByCode,
  getBalance,
  createTransaction,
  listTransactions,
  listInventory,
  getItemQuotes,
  listStock,
  createStockItem,
  addStock,
  removeStock,
  getStockSummary,
  healthCheck,
} from './services/api.js';
import { VoiceRecorder, isRecordingSupported, speak, stopSpeaking } from './services/audio.js';
import {
  addReminder,
  getReminderForCustomer,
  defaultDueInDays,
} from './features/reminders.js';
import { clearShopSession, getShopEmail, mountAuthGate, mountWelcome } from './features/login.js';
import { sourceLabel } from './features/prices.js';


const views=document.querySelectorAll('.bottomnav a');
const sections=document.querySelectorAll('.section');
const title=document.getElementById('title');
const translations={
  en:{
    home:'Home',dashboard:'Dashboard',totalSales:'Total sales',purchases:'Purchases',profit:'Profit',expenses:'Expenses',
    creditGiven:'Credit loan',creditTaken:'Taken',creditTotals:'Customer credit totals',summary:'Summary',
    summaryHint:'Open Bills for detailed reports and transactions.',profile:'Profile',language:'Language',saveChanges:'Save changes',
    name:'Name',email:'Email',phoneNumber:'Phone number',storeName:'Store name',address:'Address',openProfile:'Open profile',
    bills:'Bills',reportsSummary:'Reports summary',reportsLine:'Total sales ₹4.82L · Purchases ₹3.11L · Profit ₹1.71L',sales:'Sales',purchase:'Purchase',expense:'Expense',
    searchSalesBills:'Search sales bills...',searchPurchaseBills:'Search purchase bills...',addBill:'+ Add bill',
    bill:'Bill',date:'Date',customer:'Customer',vendor:'Vendor',amountShort:'Amount',status:'Status',paid:'Paid',pending:'Pending',
    search:'Search...',add:'+ Add',item:'Item',stock:'Stock',price:'Price',
    customers:'Customers',savedCustomerEntries:'Your saved customer credit entries',searchCustomers:'Search by customer name or phone',
    searchButton:'Search',addCustomer:'Add customer',addCustomerTitle:'Add customer',editCustomerTitle:'Edit customer',
    customerFormIntro:'Add contact details and record a credit entry.',customerName:'Customer name',creditType:'Credit type',
    amount:'Amount',amountGiven:'Amount (credit given)',amountTaken:'Amount (got)',dateTime:'Date and time',attachBill:'Attach bill',saveCustomer:'Save customer',updateCustomer:'Update customer',
    cancel:'Cancel',noCustomers:'No customers added yet. Add a customer to start tracking credit.',
    noCustomerMatches:'No customers match your search.',customerStorageLoadError:'Saved customers could not be loaded, so the list was reset. You can add customers again.',
    customerStorageUnavailable:'Customer storage is unavailable. Resolve the storage issue before saving.',
    customerStorageSaveError:'This customer could not be saved to browser storage. Check available storage and try again.',
    invalidCustomer:'Enter a valid name, phone number, amount, and date.',customerMissing:'This customer is no longer available. Return to the customer list and try again.',
    languageLoadError:'The saved language could not be loaded. English is being used.',
    languageSaveError:'The language changed for this session but could not be saved.',
    stockOut:'Out',stockLow:'Low',inStock:'In stock',
    reportSalesTitle:'Sales report',reportPurchTitle:'Purchase report',reportExpTitle:'Expense report',
    reportSalesPlaceholder:'Detailed sales report placeholder.',reportPurchPlaceholder:'Detailed purchase report placeholder.',
    reportExpPlaceholder:'Detailed expense report placeholder.',
    viewReport:'View report',reportTitle:'Business report',reportSubtitle:'Sales, purchases, profit and expenses',backToBills:'Back to bills',
    monthlyComparison:'Monthly sales & purchases',chartThousands:'Monthly totals (₹k)',monthlyChartDescription:'Monthly comparison of sales and purchases from January to June.',
    profitTrend:'Profit trend',profitThousands:'Monthly profit (₹k)',profitChartDescription:'Monthly profit trend from January to June.',
    expenseBreakdown:'Expense breakdown',expenseByCategory:'Share by category',
    expenseChartDescription:'Expenses: rent 35%, salary 28%, utilities 15%, marketing 12%, other 10%.',
    rent:'Rent',salary:'Salary',utilities:'Utilities',marketing:'Marketing',other:'Other',
    lookupByCode:'Lookup by customer ID',codePlaceholder:'e.g. RAM99',lookup:'Lookup',customerCode:'Customer ID',customerIdLabel:'ID',deleteCustomer:'Delete',confirmDelete:'Remove this customer from the active list?',customerDeleted:'Customer removed.',remind:'Remind',remindScheduled:'Reminder scheduled.',reminderOn:'Reminder on',reminderOff:'No reminder',reminderSent:'Reminder sent',fromContacts:'From contacts',phoneOnly:'Phone only',contactsUnsupported:'Contacts picker not supported here.',contactsDenied:'Could not read contacts.',phoneOnlyHint:'Name optional — phone is enough to register. ID = first 3 letters of name + last 2 digits of phone.',registeredCode:'Registered ID',idUpdated:'Customer ID updated',searchCustomers:'Search by name, phone or ID',priceCompare:'Price compare',priceCompareHint:'Manual / sample prices vs JumboTail, Flipkart, Amazon',resetPrices:'Reset samples',yourPrice:'Your price',bestDeal:'Best',priceCompareDisclaimer:'Sample data only — not live marketplace scraping.',
    todaySales:'Today credit',todayPayments:'Today payments',lowStock:'Low stock',
    addEntry:'Add entry',speakKhata:'Speak khata',speakStock:'Speak stock',
    recentActivity:'Recent activity',recentTxns:'Recent transactions',
    refreshQuotes:'Refresh quotes',noRecent:'No recent entries yet.',
    addStockPrompt:'Item name',stockQtyPrompt:'Quantity',stockAdded:'Stock item saved.'
  },
  hi:{
    home:'होम',dashboard:'डैशबोर्ड',totalSales:'कुल बिक्री',purchases:'खरीदारी',profit:'लाभ',expenses:'खर्च',
    creditGiven:'दिया गया उधार',creditTaken:'मिला हुआ उधार',creditTotals:'ग्राहक उधार का कुल योग',summary:'सारांश',
    summaryHint:'विस्तृत रिपोर्ट और लेन-देन के लिए बिल खोलें।',profile:'प्रोफ़ाइल',language:'भाषा',saveChanges:'बदलाव सहेजें',
    name:'नाम',email:'ईमेल',phoneNumber:'फ़ोन नंबर',storeName:'दुकान का नाम',address:'पता',openProfile:'प्रोफ़ाइल खोलें',
    bills:'बिल',reportsSummary:'रिपोर्ट सारांश',reportsLine:'कुल बिक्री ₹4.82L · खरीद ₹3.11L · लाभ ₹1.71L',sales:'बिक्री',purchase:'खरीद',expense:'खर्च',
    searchSalesBills:'बिक्री के बिल खोजें...',searchPurchaseBills:'खरीद के बिल खोजें...',addBill:'+ बिल जोड़ें',
    bill:'बिल',date:'तारीख',customer:'ग्राहक',vendor:'विक्रेता',amountShort:'राशि',status:'स्थिति',paid:'भुगतान हुआ',pending:'बाकी',
    search:'खोजें...',add:'+ जोड़ें',item:'वस्तु',stock:'स्टॉक',price:'कीमत',
    customers:'ग्राहक',savedCustomerEntries:'आपके सहेजे गए ग्राहक उधार रिकॉर्ड',searchCustomers:'नाम या फ़ोन से ग्राहक खोजें',
    searchButton:'खोजें',addCustomer:'ग्राहक जोड़ें',addCustomerTitle:'ग्राहक जोड़ें',editCustomerTitle:'ग्राहक संपादित करें',
    customerFormIntro:'संपर्क विवरण जोड़ें और उधार दर्ज करें।',customerName:'ग्राहक का नाम',creditType:'उधार का प्रकार',
    amount:'राशि',amountGiven:'राशि (दिया गया उधार)',amountTaken:'राशि (मिला हुआ उधार)',dateTime:'तारीख और समय',attachBill:'बिल संलग्न करें',saveCustomer:'ग्राहक सहेजें',updateCustomer:'ग्राहक अपडेट करें',
    cancel:'रद्द करें',noCustomers:'अभी कोई ग्राहक नहीं है। उधार ट्रैक करने के लिए ग्राहक जोड़ें।',
    noCustomerMatches:'आपकी खोज से कोई ग्राहक नहीं मिला।',customerStorageLoadError:'सहेजे गए ग्राहक लोड नहीं हो सके, इसलिए सूची रीसेट कर दी गई है। आप फिर से ग्राहक जोड़ सकते हैं।',
    customerStorageUnavailable:'ग्राहक स्टोरेज उपलब्ध नहीं है। सहेजने से पहले समस्या ठीक करें।',
    customerStorageSaveError:'ग्राहक ब्राउज़र स्टोरेज में सहेजा नहीं जा सका। स्टोरेज जांचकर फिर कोशिश करें।',
    invalidCustomer:'मान्य नाम, फ़ोन नंबर, राशि और तारीख दर्ज करें।',customerMissing:'यह ग्राहक अब उपलब्ध नहीं है। ग्राहक सूची पर लौटकर फिर कोशिश करें।',
    languageLoadError:'सहेजी गई भाषा लोड नहीं हो सकी। अंग्रेज़ी का उपयोग किया जा रहा है।',
    languageSaveError:'इस सत्र के लिए भाषा बदल गई है, लेकिन बदलाव सहेजा नहीं जा सका।',
    stockOut:'खत्म',stockLow:'कम',inStock:'उपलब्ध',
    reportSalesTitle:'बिक्री रिपोर्ट',reportPurchTitle:'खरीद रिपोर्ट',reportExpTitle:'खर्च रिपोर्ट',
    reportSalesPlaceholder:'विस्तृत बिक्री रिपोर्ट।',reportPurchPlaceholder:'विस्तृत खरीद रिपोर्ट।',reportExpPlaceholder:'विस्तृत खर्च रिपोर्ट।',
    viewReport:'रिपोर्ट देखें',reportTitle:'व्यापार रिपोर्ट',reportSubtitle:'बिक्री, खरीद, लाभ और खर्च',backToBills:'बिल पर वापस जाएँ',
    monthlyComparison:'मासिक बिक्री और खरीद',chartThousands:'मासिक कुल (₹ हज़ार)',monthlyChartDescription:'जनवरी से जून तक बिक्री और खरीद की मासिक तुलना।',
    profitTrend:'लाभ का रुझान',profitThousands:'मासिक लाभ (₹ हज़ार)',profitChartDescription:'जनवरी से जून तक मासिक लाभ का रुझान।',
    expenseBreakdown:'खर्च का विवरण',expenseByCategory:'श्रेणी के अनुसार हिस्सा',
    expenseChartDescription:'खर्च: किराया 35%, वेतन 28%, उपयोगिताएँ 15%, मार्केटिंग 12%, अन्य 10%.',
    rent:'किराया',salary:'वेतन',utilities:'उपयोगिताएँ',marketing:'मार्केटिंग',other:'अन्य'
  },
  bn:{
    home:'হোম',dashboard:'ড্যাশবোর্ড',totalSales:'মোট বিক্রয়',purchases:'কেনাকাটা',profit:'লাভ',expenses:'খরচ',
    creditGiven:'দেওয়া ধার',creditTaken:'পাওয়া ধার',creditTotals:'গ্রাহক ধার মোট',summary:'সারাংশ',
    summaryHint:'বিস্তারিত প্রতিবেদন ও লেনদেনের জন্য বিল খুলুন।',profile:'প্রোফাইল',language:'ভাষা',saveChanges:'পরিবর্তন সংরক্ষণ',
    name:'নাম',email:'ইমেল',phoneNumber:'ফোন নম্বর',storeName:'দোকানের নাম',address:'ঠিকানা',openProfile:'প্রোফাইল খুলুন',
    bills:'বিল',reportsSummary:'প্রতিবেদনের সারাংশ',reportsLine:'মোট বিক্রয় ₹4.82L · কেনাকাটা ₹3.11L · লাভ ₹1.71L',sales:'বিক্রয়',purchase:'কেনাকাটা',expense:'খরচ',
    searchSalesBills:'বিক্রয় বিল খুঁজুন...',searchPurchaseBills:'কেনাকাটার বিল খুঁজুন...',addBill:'+ বিল যোগ করুন',
    bill:'বিল',date:'তারিখ',customer:'গ্রাহক',vendor:'বিক্রেতা',amountShort:'পরিমাণ',status:'অবস্থা',paid:'পরিশোধিত',pending:'বাকি',
    search:'খুঁজুন...',add:'+ যোগ করুন',item:'পণ্য',stock:'স্টক',price:'দাম',
    customers:'গ্রাহক',savedCustomerEntries:'সংরক্ষিত গ্রাহকের ধার হিসাব',searchCustomers:'নাম বা ফোন দিয়ে গ্রাহক খুঁজুন',
    searchButton:'খুঁজুন',addCustomer:'গ্রাহক যোগ করুন',addCustomerTitle:'গ্রাহক যোগ করুন',editCustomerTitle:'গ্রাহক সম্পাদনা',
    customerFormIntro:'যোগাযোগের তথ্য ও ধার হিসাব যোগ করুন।',customerName:'গ্রাহকের নাম',creditType:'ধারের ধরন',
    amount:'পরিমাণ',amountGiven:'পরিমাণ (দেওয়া ধার)',amountTaken:'পরিমাণ (পাওয়া ধার)',dateTime:'তারিখ ও সময়',attachBill:'বিল সংযুক্ত করুন',saveCustomer:'গ্রাহক সংরক্ষণ',updateCustomer:'গ্রাহক আপডেট',
    cancel:'বাতিল',noCustomers:'এখনও কোনো গ্রাহক নেই। ধার হিসাব রাখতে গ্রাহক যোগ করুন।',
    noCustomerMatches:'আপনার অনুসন্ধানে কোনো গ্রাহক মেলেনি।',customerStorageLoadError:'সংরক্ষিত গ্রাহক লোড করা যায়নি, তাই তালিকা রিসেট করা হয়েছে। আপনি আবার গ্রাহক যোগ করতে পারেন।',
    customerStorageUnavailable:'গ্রাহক স্টোরেজ উপলভ্য নয়। সংরক্ষণের আগে সমস্যাটি সমাধান করুন।',
    customerStorageSaveError:'ব্রাউজার স্টোরেজে গ্রাহক সংরক্ষণ করা যায়নি। জায়গা পরীক্ষা করে আবার চেষ্টা করুন।',
    invalidCustomer:'সঠিক নাম, ফোন নম্বর, পরিমাণ এবং তারিখ দিন।',customerMissing:'এই গ্রাহক আর উপলভ্য নেই। গ্রাহক তালিকায় ফিরে আবার চেষ্টা করুন।',
    languageLoadError:'সংরক্ষিত ভাষা লোড করা যায়নি। ইংরেজি ব্যবহার করা হচ্ছে।',
    languageSaveError:'এই সেশনের জন্য ভাষা বদলেছে, তবে সংরক্ষণ করা যায়নি।',
    stockOut:'শেষ',stockLow:'কম',inStock:'মজুত আছে',
    reportSalesTitle:'বিক্রয় প্রতিবেদন',reportPurchTitle:'কেনাকাটার প্রতিবেদন',reportExpTitle:'খরচের প্রতিবেদন',
    reportSalesPlaceholder:'বিস্তারিত বিক্রয় প্রতিবেদন।',reportPurchPlaceholder:'বিস্তারিত কেনাকাটার প্রতিবেদন।',reportExpPlaceholder:'বিস্তারিত খরচের প্রতিবেদন।',
    viewReport:'প্রতিবেদন দেখুন',reportTitle:'ব্যবসার প্রতিবেদন',reportSubtitle:'বিক্রয়, কেনাকাটা, লাভ ও খরচ',backToBills:'বিলে ফিরে যান',
    monthlyComparison:'মাসিক বিক্রয় ও কেনাকাটা',chartThousands:'মাসিক মোট (₹ হাজার)',monthlyChartDescription:'জানুয়ারি থেকে জুন পর্যন্ত বিক্রয় ও কেনাকাটার তুলনা।',
    profitTrend:'লাভের প্রবণতা',profitThousands:'মাসিক লাভ (₹ হাজার)',profitChartDescription:'জানুয়ারি থেকে জুন পর্যন্ত মাসিক লাভের প্রবণতা।',
    expenseBreakdown:'খরচের বিবরণ',expenseByCategory:'বিভাগ অনুযায়ী অংশ',
    expenseChartDescription:'খরচ: ভাড়া ৩৫%, বেতন ২৮%, ইউটিলিটি ১৫%, বিপণন ১২%, অন্যান্য ১০%।',
    rent:'ভাড়া',salary:'বেতন',utilities:'ইউটিলিটি',marketing:'বিপণন',other:'অন্যান্য'
  },
  mr:{
    home:'मुख्यपृष्ठ',dashboard:'डॅशबोर्ड',totalSales:'एकूण विक्री',purchases:'खरेदी',profit:'नफा',expenses:'खर्च',
    creditGiven:'दिलेली उधारी',creditTaken:'मिळालेली उधारी',creditTotals:'ग्राहक उधारीची एकूण रक्कम',summary:'सारांश',
    summaryHint:'तपशीलवार अहवाल आणि व्यवहारांसाठी बिले उघडा.',profile:'प्रोफाइल',language:'भाषा',saveChanges:'बदल जतन करा',
    name:'नाव',email:'ईमेल',phoneNumber:'फोन नंबर',storeName:'दुकानाचे नाव',address:'पत्ता',openProfile:'प्रोफाइल उघडा',
    bills:'बिले',reportsSummary:'अहवालाचा सारांश',reportsLine:'एकूण विक्री ₹4.82L · खरेदी ₹3.11L · नफा ₹1.71L',sales:'विक्री',purchase:'खरेदी',expense:'खर्च',
    searchSalesBills:'विक्रीची बिले शोधा...',searchPurchaseBills:'खरेदीची बिले शोधा...',addBill:'+ बिल जोडा',
    bill:'बिल',date:'तारीख',customer:'ग्राहक',vendor:'विक्रेता',amountShort:'रक्कम',status:'स्थिती',paid:'भरले',pending:'प्रलंबित',
    search:'शोधा...',add:'+ जोडा',item:'वस्तू',stock:'साठा',price:'किंमत',
    customers:'ग्राहक',savedCustomerEntries:'जतन केलेल्या ग्राहक उधारी नोंदी',searchCustomers:'नाव किंवा फोनने ग्राहक शोधा',
    searchButton:'शोधा',addCustomer:'ग्राहक जोडा',addCustomerTitle:'ग्राहक जोडा',editCustomerTitle:'ग्राहक संपादित करा',
    customerFormIntro:'संपर्क तपशील जोडा आणि उधारी नोंदवा.',customerName:'ग्राहकाचे नाव',creditType:'उधारीचा प्रकार',
    amount:'रक्कम',amountGiven:'रक्कम (दिलेली उधारी)',amountTaken:'रक्कम (मिळालेली उधारी)',dateTime:'तारीख आणि वेळ',attachBill:'बिल जोडा',saveCustomer:'ग्राहक जतन करा',updateCustomer:'ग्राहक अद्यतनित करा',
    cancel:'रद्द करा',noCustomers:'अजून ग्राहक जोडलेले नाहीत. उधारीचा मागोवा घेण्यासाठी ग्राहक जोडा.',
    noCustomerMatches:'तुमच्या शोधाशी जुळणारा ग्राहक नाही.',customerStorageLoadError:'जतन केलेले ग्राहक लोड करता आले नाहीत, म्हणून यादी रीसेट केली आहे. तुम्ही पुन्हा ग्राहक जोडू शकता.',
    customerStorageUnavailable:'ग्राहक स्टोरेज उपलब्ध नाही. जतन करण्यापूर्वी समस्या सोडवा.',
    customerStorageSaveError:'ग्राहक ब्राउझर स्टोरेजमध्ये जतन करता आला नाही. स्टोरेज तपासून पुन्हा प्रयत्न करा.',
    invalidCustomer:'योग्य नाव, फोन नंबर, रक्कम आणि तारीख भरा.',customerMissing:'हा ग्राहक आता उपलब्ध नाही. ग्राहक यादीवर परत जाऊन पुन्हा प्रयत्न करा.',
    languageLoadError:'जतन केलेली भाषा लोड करता आली नाही. इंग्रजी वापरली जात आहे.',
    languageSaveError:'या सत्रासाठी भाषा बदलली आहे, पण जतन करता आली नाही.',
    stockOut:'संपले',stockLow:'कमी',inStock:'उपलब्ध',
    reportSalesTitle:'विक्री अहवाल',reportPurchTitle:'खरेदी अहवाल',reportExpTitle:'खर्च अहवाल',
    reportSalesPlaceholder:'तपशीलवार विक्री अहवाल.',reportPurchPlaceholder:'तपशीलवार खरेदी अहवाल.',reportExpPlaceholder:'तपशीलवार खर्च अहवाल.',
    viewReport:'अहवाल पहा',reportTitle:'व्यवसाय अहवाल',reportSubtitle:'विक्री, खरेदी, नफा आणि खर्च',backToBills:'बिलांकडे परत जा',
    monthlyComparison:'मासिक विक्री आणि खरेदी',chartThousands:'मासिक एकूण (₹ हजार)',monthlyChartDescription:'जानेवारी ते जूनमधील विक्री आणि खरेदीची तुलना.',
    profitTrend:'नफ्याचा कल',profitThousands:'मासिक नफा (₹ हजार)',profitChartDescription:'जानेवारी ते जूनमधील मासिक नफ्याचा कल.',
    expenseBreakdown:'खर्चाचा तपशील',expenseByCategory:'वर्गानुसार वाटा',
    expenseChartDescription:'खर्च: भाडे ३५%, पगार २८%, सुविधा १५%, विपणन १२%, इतर १०%.',
    rent:'भाडे',salary:'पगार',utilities:'सुविधा',marketing:'विपणन',other:'इतर'
  },
  te:{
    home:'హోమ్',dashboard:'డాష్‌బోర్డ్',totalSales:'మొత్తం అమ్మకాలు',purchases:'కొనుగోళ్లు',profit:'లాభం',expenses:'ఖర్చులు',
    creditGiven:'ఇచ్చిన అప్పు',creditTaken:'వచ్చిన అప్పు',creditTotals:'కస్టమర్ అప్పుల మొత్తం',summary:'సారాంశం',
    summaryHint:'వివరమైన నివేదికలు, లావాదేవీల కోసం బిల్లులు తెరవండి.',profile:'ప్రొఫైల్',language:'భాష',saveChanges:'మార్పులను భద్రపరచండి',
    name:'పేరు',email:'ఇమెయిల్',phoneNumber:'ఫోన్ నంబర్',storeName:'దుకాణం పేరు',address:'చిరునామా',openProfile:'ప్రొఫైల్ తెరవండి',
    bills:'బిల్లులు',reportsSummary:'నివేదికల సారాంశం',reportsLine:'మొత్తం అమ్మకాలు ₹4.82L · కొనుగోళ్లు ₹3.11L · లాభం ₹1.71L',sales:'అమ్మకాలు',purchase:'కొనుగోలు',expense:'ఖర్చు',
    searchSalesBills:'అమ్మకాల బిల్లులను వెతకండి...',searchPurchaseBills:'కొనుగోలు బిల్లులను వెతకండి...',addBill:'+ బిల్లు జోడించండి',
    bill:'బిల్లు',date:'తేదీ',customer:'కస్టమర్',vendor:'విక్రేత',amountShort:'మొత్తం',status:'స్థితి',paid:'చెల్లించబడింది',pending:'పెండింగ్',
    search:'వెతకండి...',add:'+ జోడించండి',item:'వస్తువు',stock:'నిల్వ',price:'ధర',
    customers:'కస్టమర్లు',savedCustomerEntries:'మీరు భద్రపరిచిన కస్టమర్ అప్పు వివరాలు',searchCustomers:'పేరు లేదా ఫోన్‌తో వెతకండి',
    searchButton:'వెతకండి',addCustomer:'కస్టమర్‌ను జోడించండి',addCustomerTitle:'కస్టమర్‌ను జోడించండి',editCustomerTitle:'కస్టమర్ వివరాలను సవరించండి',
    customerFormIntro:'సంప్రదింపు వివరాలు జోడించి అప్పును నమోదు చేయండి.',customerName:'కస్టమర్ పేరు',creditType:'అప్పు రకం',
    amount:'మొత్తం',amountGiven:'మొత్తం (ఇచ్చిన అప్పు)',amountTaken:'మొత్తం (వచ్చిన అప్పు)',dateTime:'తేదీ మరియు సమయం',attachBill:'బిల్లును జతచేయండి',saveCustomer:'కస్టమర్‌ను భద్రపరచండి',updateCustomer:'కస్టమర్‌ను నవీకరించండి',
    cancel:'రద్దు చేయండి',noCustomers:'ఇంకా కస్టమర్లు లేరు. అప్పులను ట్రాక్ చేయడానికి కస్టమర్‌ను జోడించండి.',
    noCustomerMatches:'మీ శోధనకు కస్టమర్లు సరిపోలలేదు.',customerStorageLoadError:'భద్రపరిచిన కస్టమర్లను లోడ్ చేయలేకపోయాం, కాబట్టి జాబితా రీసెట్ అయింది. మీరు మళ్లీ కస్టమర్లను జోడించవచ్చు.',
    customerStorageUnavailable:'కస్టమర్ నిల్వ అందుబాటులో లేదు. భద్రపరచే ముందు సమస్యను పరిష్కరించండి.',
    customerStorageSaveError:'బ్రౌజర్ నిల్వలో కస్టమర్‌ను భద్రపరచలేకపోయాం. నిల్వను తనిఖీ చేసి మళ్లీ ప్రయత్నించండి.',
    invalidCustomer:'సరైన పేరు, ఫోన్ నంబర్, మొత్తం, తేదీ నమోదు చేయండి.',customerMissing:'ఈ కస్టమర్ ఇప్పుడు అందుబాటులో లేరు. కస్టమర్ల జాబితాకు వెళ్లి మళ్లీ ప్రయత్నించండి.',
    languageLoadError:'భద్రపరిచిన భాషను లోడ్ చేయలేకపోయాం. ఇంగ్లీష్ ఉపయోగిస్తున్నాం.',
    languageSaveError:'ఈ సెషన్‌కు భాష మారింది, కానీ మార్పును భద్రపరచలేకపోయాం.',
    stockOut:'అయిపోయింది',stockLow:'తక్కువ',inStock:'స్టాక్‌లో ఉంది',
    reportSalesTitle:'అమ్మకాల నివేదిక',reportPurchTitle:'కొనుగోలు నివేదిక',reportExpTitle:'ఖర్చుల నివేదిక',
    reportSalesPlaceholder:'వివరమైన అమ్మకాల నివేదిక.',reportPurchPlaceholder:'వివరమైన కొనుగోలు నివేదిక.',reportExpPlaceholder:'వివరమైన ఖర్చుల నివేదిక.',
    viewReport:'నివేదికను చూడండి',reportTitle:'వ్యాపార నివేదిక',reportSubtitle:'అమ్మకాలు, కొనుగోళ్లు, లాభం మరియు ఖర్చులు',backToBills:'బిల్లులకు తిరిగి వెళ్లండి',
    monthlyComparison:'నెలవారీ అమ్మకాలు మరియు కొనుగోళ్లు',chartThousands:'నెలవారీ మొత్తం (₹ వేలల్లో)',monthlyChartDescription:'జనవరి నుండి జూన్ వరకు అమ్మకాలు, కొనుగోళ్ల పోలిక.',
    profitTrend:'లాభ ధోరణి',profitThousands:'నెలవారీ లాభం (₹ వేలల్లో)',profitChartDescription:'జనవరి నుండి జూన్ వరకు నెలవారీ లాభ ధోరణి.',
    expenseBreakdown:'ఖర్చుల వివరాలు',expenseByCategory:'వర్గాల వారీగా వాటా',
    expenseChartDescription:'ఖర్చులు: అద్దె 35%, జీతం 28%, యుటిలిటీలు 15%, మార్కెటింగ్ 12%, ఇతరాలు 10%.',
    rent:'అద్దె',salary:'జీతం',utilities:'యుటిలిటీలు',marketing:'మార్కెటింగ్',other:'ఇతరాలు'
  },
  kn:{
    home:'ಮುಖಪುಟ',dashboard:'ಡ್ಯಾಶ್‌ಬೋರ್ಡ್',totalSales:'ಒಟ್ಟು ಮಾರಾಟ',purchases:'ಖರೀದಿಗಳು',profit:'ಲಾಭ',expenses:'ಖರ್ಚುಗಳು',
    creditGiven:'ನೀಡಿದ ಸಾಲ',creditTaken:'ಪಡೆದ ಸಾಲ',creditTotals:'ಗ್ರಾಹಕರ ಸಾಲದ ಒಟ್ಟು',summary:'ಸಾರಾಂಶ',
    summaryHint:'ವಿವರವಾದ ವರದಿಗಳು ಮತ್ತು ವಹಿವಾಟುಗಳಿಗಾಗಿ ಬಿಲ್‌ಗಳನ್ನು ತೆರೆಯಿರಿ.',profile:'ಪ್ರೊಫೈಲ್',language:'ಭಾಷೆ',saveChanges:'ಬದಲಾವಣೆಗಳನ್ನು ಉಳಿಸಿ',
    name:'ಹೆಸರು',email:'ಇಮೇಲ್',phoneNumber:'ಫೋನ್ ಸಂಖ್ಯೆ',storeName:'ಅಂಗಡಿಯ ಹೆಸರು',address:'ವಿಳಾಸ',openProfile:'ಪ್ರೊಫೈಲ್ ತೆರೆಯಿರಿ',
    bills:'ಬಿಲ್‌ಗಳು',reportsSummary:'ವರದಿಗಳ ಸಾರಾಂಶ',reportsLine:'ಒಟ್ಟು ಮಾರಾಟ ₹4.82L · ಖರೀದಿ ₹3.11L · ಲಾಭ ₹1.71L',sales:'ಮಾರಾಟ',purchase:'ಖರೀದಿ',expense:'ಖರ್ಚು',
    searchSalesBills:'ಮಾರಾಟದ ಬಿಲ್‌ಗಳನ್ನು ಹುಡುಕಿ...',searchPurchaseBills:'ಖರೀದಿ ಬಿಲ್‌ಗಳನ್ನು ಹುಡುಕಿ...',addBill:'+ ಬಿಲ್ ಸೇರಿಸಿ',
    bill:'ಬಿಲ್',date:'ದಿನಾಂಕ',customer:'ಗ್ರಾಹಕ',vendor:'ಮಾರಾಟಗಾರ',amountShort:'ಮೊತ್ತ',status:'ಸ್ಥಿತಿ',paid:'ಪಾವತಿಸಲಾಗಿದೆ',pending:'ಬಾಕಿ',
    search:'ಹುಡುಕಿ...',add:'+ ಸೇರಿಸಿ',item:'ವಸ್ತು',stock:'ಸ್ಟಾಕ್',price:'ಬೆಲೆ',
    customers:'ಗ್ರಾಹಕರು',savedCustomerEntries:'ನೀವು ಉಳಿಸಿದ ಗ್ರಾಹಕರ ಸಾಲದ ನಮೂದುಗಳು',searchCustomers:'ಹೆಸರು ಅಥವಾ ಫೋನ್‌ನಿಂದ ಹುಡುಕಿ',
    searchButton:'ಹುಡುಕಿ',addCustomer:'ಗ್ರಾಹಕರನ್ನು ಸೇರಿಸಿ',addCustomerTitle:'ಗ್ರಾಹಕರನ್ನು ಸೇರಿಸಿ',editCustomerTitle:'ಗ್ರಾಹಕರ ವಿವರಗಳನ್ನು ಸಂಪಾದಿಸಿ',
    customerFormIntro:'ಸಂಪರ್ಕ ವಿವರಗಳನ್ನು ಸೇರಿಸಿ ಮತ್ತು ಸಾಲವನ್ನು ದಾಖಲಿಸಿ.',customerName:'ಗ್ರಾಹಕರ ಹೆಸರು',creditType:'ಸಾಲದ ಪ್ರಕಾರ',
    amount:'ಮೊತ್ತ',amountGiven:'ಮೊತ್ತ (ನೀಡಿದ ಸಾಲ)',amountTaken:'ಮೊತ್ತ (ಪಡೆದ ಸಾಲ)',dateTime:'ದಿನಾಂಕ ಮತ್ತು ಸಮಯ',attachBill:'ಬಿಲ್ ಲಗತ್ತಿಸಿ',saveCustomer:'ಗ್ರಾಹಕರನ್ನು ಉಳಿಸಿ',updateCustomer:'ಗ್ರಾಹಕರನ್ನು ನವೀಕರಿಸಿ',
    cancel:'ರದ್ದುಮಾಡಿ',noCustomers:'ಇನ್ನೂ ಗ್ರಾಹಕರಿಲ್ಲ. ಸಾಲವನ್ನು ಟ್ರ್ಯಾಕ್ ಮಾಡಲು ಗ್ರಾಹಕರನ್ನು ಸೇರಿಸಿ.',
    noCustomerMatches:'ನಿಮ್ಮ ಹುಡುಕಾಟಕ್ಕೆ ಗ್ರಾಹಕರು ಹೊಂದಿಕೆಯಾಗಲಿಲ್ಲ.',customerStorageLoadError:'ಉಳಿಸಿದ ಗ್ರಾಹಕರನ್ನು ಲೋಡ್ ಮಾಡಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ, ಆದ್ದರಿಂದ ಪಟ್ಟಿಯನ್ನು ಮರುಹೊಂದಿಸಲಾಗಿದೆ. ನೀವು ಮತ್ತೆ ಗ್ರಾಹಕರನ್ನು ಸೇರಿಸಬಹುದು.',
    customerStorageUnavailable:'ಗ್ರಾಹಕರ ಸಂಗ್ರಹ ಲಭ್ಯವಿಲ್ಲ. ಉಳಿಸುವ ಮೊದಲು ಸಮಸ್ಯೆಯನ್ನು ಪರಿಹರಿಸಿ.',
    customerStorageSaveError:'ಬ್ರೌಸರ್ ಸಂಗ್ರಹದಲ್ಲಿ ಗ್ರಾಹಕರನ್ನು ಉಳಿಸಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ. ಸಂಗ್ರಹವನ್ನು ಪರಿಶೀಲಿಸಿ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.',
    invalidCustomer:'ಸರಿಯಾದ ಹೆಸರು, ಫೋನ್ ಸಂಖ್ಯೆ, ಮೊತ್ತ ಮತ್ತು ದಿನಾಂಕವನ್ನು ನಮೂದಿಸಿ.',customerMissing:'ಈ ಗ್ರಾಹಕರು ಈಗ ಲಭ್ಯವಿಲ್ಲ. ಗ್ರಾಹಕರ ಪಟ್ಟಿಗೆ ಹಿಂತಿರುಗಿ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.',
    languageLoadError:'ಉಳಿಸಿದ ಭಾಷೆಯನ್ನು ಲೋಡ್ ಮಾಡಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ. ಇಂಗ್ಲಿಷ್ ಬಳಸಲಾಗುತ್ತಿದೆ.',
    languageSaveError:'ಈ ಅಧಿವೇಶನಕ್ಕೆ ಭಾಷೆ ಬದಲಾಗಿದೆ, ಆದರೆ ಉಳಿಸಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ.',
    stockOut:'ಮುಗಿದಿದೆ',stockLow:'ಕಡಿಮೆ',inStock:'ಸ್ಟಾಕ್‌ನಲ್ಲಿದೆ',
    reportSalesTitle:'ಮಾರಾಟದ ವರದಿ',reportPurchTitle:'ಖರೀದಿ ವರದಿ',reportExpTitle:'ಖರ್ಚಿನ ವರದಿ',
    reportSalesPlaceholder:'ವಿವರವಾದ ಮಾರಾಟದ ವರದಿ.',reportPurchPlaceholder:'ವಿವರವಾದ ಖರೀದಿ ವರದಿ.',reportExpPlaceholder:'ವಿವರವಾದ ಖರ್ಚಿನ ವರದಿ.',
    viewReport:'ವರದಿ ನೋಡಿ',reportTitle:'ವ್ಯಾಪಾರ ವರದಿ',reportSubtitle:'ಮಾರಾಟ, ಖರೀದಿ, ಲಾಭ ಮತ್ತು ಖರ್ಚುಗಳು',backToBills:'ಬಿಲ್‌ಗಳಿಗೆ ಹಿಂತಿರುಗಿ',
    monthlyComparison:'ಮಾಸಿಕ ಮಾರಾಟ ಮತ್ತು ಖರೀದಿ',chartThousands:'ಮಾಸಿಕ ಒಟ್ಟು (₹ ಸಾವಿರ)',monthlyChartDescription:'ಜನವರಿಯಿಂದ ಜೂನ್‌ವರೆಗೆ ಮಾರಾಟ ಮತ್ತು ಖರೀದಿಯ ಮಾಸಿಕ ಹೋಲಿಕೆ.',
    profitTrend:'ಲಾಭದ ಪ್ರವೃತ್ತಿ',profitThousands:'ಮಾಸಿಕ ಲಾಭ (₹ ಸಾವಿರ)',profitChartDescription:'ಜನವರಿಯಿಂದ ಜೂನ್‌ವರೆಗೆ ಮಾಸಿಕ ಲಾಭದ ಪ್ರವೃತ್ತಿ.',
    expenseBreakdown:'ಖರ್ಚಿನ ವಿವರ',expenseByCategory:'ವರ್ಗದ ಪ್ರಕಾರ ಪಾಲು',
    expenseChartDescription:'ಖರ್ಚುಗಳು: ಬಾಡಿಗೆ 35%, ಸಂಬಳ 28%, ಉಪಯುಕ್ತತೆಗಳು 15%, ಮಾರ್ಕೆಟಿಂಗ್ 12%, ಇತರೆ 10%.',
    rent:'ಬಾಡಿಗೆ',salary:'ಸಂಬಳ',utilities:'ಉಪಯುಕ್ತತೆಗಳು',marketing:'ಮಾರ್ಕೆಟಿಂಗ್',other:'ಇತರೆ'
  },
  ta:{
    home:'முகப்பு',dashboard:'டாஷ்போர்டு',totalSales:'மொத்த விற்பனை',purchases:'கொள்முதல்',profit:'லாபம்',expenses:'செலவுகள்',
    creditGiven:'கொடுத்த கடன்',creditTaken:'பெற்ற கடன்',creditTotals:'வாடிக்கையாளர் கடன் மொத்தம்',summary:'சுருக்கம்',
    summaryHint:'விரிவான அறிக்கைகள் மற்றும் பரிவர்த்தனைகளுக்கு பில்களைத் திறக்கவும்.',profile:'சுயவிவரம்',language:'மொழி',saveChanges:'மாற்றங்களைச் சேமிக்கவும்',
    name:'பெயர்',email:'மின்னஞ்சல்',phoneNumber:'தொலைபேசி எண்',storeName:'கடை பெயர்',address:'முகவரி',openProfile:'சுயவிவரத்தைத் திறக்கவும்',
    bills:'பில்கள்',reportsSummary:'அறிக்கை சுருக்கம்',reportsLine:'மொத்த விற்பனை ₹4.82L · கொள்முதல் ₹3.11L · லாபம் ₹1.71L',sales:'விற்பனை',purchase:'கொள்முதல்',expense:'செலவு',
    searchSalesBills:'விற்பனை பில்களைத் தேடுங்கள்...',searchPurchaseBills:'கொள்முதல் பில்களைத் தேடுங்கள்...',addBill:'+ பில் சேர்க்கவும்',
    bill:'பில்',date:'தேதி',customer:'வாடிக்கையாளர்',vendor:'விற்பனையாளர்',amountShort:'தொகை',status:'நிலை',paid:'செலுத்தப்பட்டது',pending:'நிலுவை',
    search:'தேடுங்கள்...',add:'+ சேர்க்கவும்',item:'பொருள்',stock:'இருப்பு',price:'விலை',
    customers:'வாடிக்கையாளர்கள்',savedCustomerEntries:'சேமித்த வாடிக்கையாளர் கடன் பதிவுகள்',searchCustomers:'பெயர் அல்லது தொலைபேசி மூலம் தேடுங்கள்',
    searchButton:'தேடுங்கள்',addCustomer:'வாடிக்கையாளரைச் சேர்க்கவும்',addCustomerTitle:'வாடிக்கையாளரைச் சேர்க்கவும்',editCustomerTitle:'வாடிக்கையாளர் விவரங்களைத் திருத்தவும்',
    customerFormIntro:'தொடர்பு விவரங்களைச் சேர்த்து கடனைப் பதிவு செய்யவும்.',customerName:'வாடிக்கையாளர் பெயர்',creditType:'கடன் வகை',
    amount:'தொகை',amountGiven:'தொகை (கொடுத்த கடன்)',amountTaken:'தொகை (பெற்ற கடன்)',dateTime:'தேதி மற்றும் நேரம்',attachBill:'பில்லை இணைக்கவும்',saveCustomer:'வாடிக்கையாளரைச் சேமிக்கவும்',updateCustomer:'வாடிக்கையாளரைப் புதுப்பிக்கவும்',
    cancel:'ரத்துசெய்',noCustomers:'வாடிக்கையாளர்கள் இன்னும் சேர்க்கப்படவில்லை. கடனைக் கண்காணிக்க ஒருவரைச் சேர்க்கவும்.',
    noCustomerMatches:'உங்கள் தேடலுக்கு வாடிக்கையாளர்கள் பொருந்தவில்லை.',customerStorageLoadError:'சேமித்த வாடிக்கையாளர்களை ஏற்ற முடியவில்லை, எனவே பட்டியல் மீட்டமைக்கப்பட்டது. நீங்கள் மீண்டும் வாடிக்கையாளர்களைச் சேர்க்கலாம்.',
    customerStorageUnavailable:'வாடிக்கையாளர் சேமிப்பகம் கிடைக்கவில்லை. சேமிப்பதற்கு முன் சிக்கலைச் சரிசெய்யவும்.',
    customerStorageSaveError:'உலாவி சேமிப்பகத்தில் வாடிக்கையாளரைச் சேமிக்க முடியவில்லை. இடத்தைச் சரிபார்த்து மீண்டும் முயற்சிக்கவும்.',
    invalidCustomer:'சரியான பெயர், தொலைபேசி எண், தொகை மற்றும் தேதியை உள்ளிடவும்.',customerMissing:'இந்த வாடிக்கையாளர் இப்போது இல்லை. வாடிக்கையாளர் பட்டியலுக்குச் சென்று மீண்டும் முயற்சிக்கவும்.',
    languageLoadError:'சேமித்த மொழியை ஏற்ற முடியவில்லை. ஆங்கிலம் பயன்படுத்தப்படுகிறது.',
    languageSaveError:'இந்த அமர்வுக்கு மொழி மாறியது, ஆனால் சேமிக்க முடியவில்லை.',
    stockOut:'கையிருப்பில்லை',stockLow:'குறைவு',inStock:'கையிருப்பில் உள்ளது',
    reportSalesTitle:'விற்பனை அறிக்கை',reportPurchTitle:'கொள்முதல் அறிக்கை',reportExpTitle:'செலவு அறிக்கை',
    reportSalesPlaceholder:'விரிவான விற்பனை அறிக்கை.',reportPurchPlaceholder:'விரிவான கொள்முதல் அறிக்கை.',reportExpPlaceholder:'விரிவான செலவு அறிக்கை.',
    viewReport:'அறிக்கையைப் பார்க்கவும்',reportTitle:'வணிக அறிக்கை',reportSubtitle:'விற்பனை, கொள்முதல், லாபம் மற்றும் செலவுகள்',backToBills:'பில்களுக்குத் திரும்பு',
    monthlyComparison:'மாதாந்திர விற்பனை மற்றும் கொள்முதல்',chartThousands:'மாத மொத்தம் (₹ ஆயிரம்)',monthlyChartDescription:'ஜனவரி முதல் ஜூன் வரை விற்பனை மற்றும் கொள்முதல் ஒப்பீடு.',
    profitTrend:'லாபப் போக்கு',profitThousands:'மாத லாபம் (₹ ஆயிரம்)',profitChartDescription:'ஜனவரி முதல் ஜூன் வரை மாதாந்திர லாபப் போக்கு.',
    expenseBreakdown:'செலவு விவரம்',expenseByCategory:'வகை வாரியான பங்கு',
    expenseChartDescription:'செலவுகள்: வாடகை 35%, சம்பளம் 28%, பயன்பாடுகள் 15%, சந்தைப்படுத்தல் 12%, மற்றவை 10%.',
    rent:'வாடகை',salary:'சம்பளம்',utilities:'பயன்பாடுகள்',marketing:'சந்தைப்படுத்தல்',other:'மற்றவை'
  },
  or:{
    home:'ହୋମ୍',dashboard:'ଡ୍ୟାସବୋର୍ଡ',creditGiven:'ଦିଆଯାଇଥିବା ଋଣ',creditTaken:'ନିଆଯାଇଥିବା',customers:'ଗ୍ରାହକ',
    addCustomer:'ଗ୍ରାହକ ଯୋଡନ୍ତୁ',searchButton:'ଖୋଜନ୍ତୁ',language:'ଭାଷା',profile:'ପ୍ରୋଫାଇଲ୍',
    lookupByCode:'ଗ୍ରାହକ ID ରେ ଖୋଜନ୍ତୁ',lookup:'ଖୋଜନ୍ତୁ',deleteCustomer:'ଡିଲିଟ୍',remind:'ରିମାଇଣ୍ଡ',
    reminders:'ବାକି ରିମାଇଣ୍ଡର',fromContacts:'କଣ୍ଟାକ୍ଟରୁ',phoneOnly:'କେବଳ ଫୋନ୍',priceCompare:'ମୂଲ୍ୟ ତୁଳନା',
    stock:'ଷ୍ଟକ୍',bills:'ବିଲ୍',saveCustomer:'ଗ୍ରାହକ ସେଭ୍ କରନ୍ତୁ',cancel:'ବାତିଲ୍'
  },
  ml:{
    home:'ഹോം',dashboard:'ഡാഷ്ബോർഡ്',creditGiven:'കൊടുത്ത ക്രെഡിറ്റ്',creditTaken:'ലഭിച്ചത്',customers:'ഉപഭോക്താക്കൾ',
    addCustomer:'ഉപഭോക്താവിനെ ചേർക്കുക',searchButton:'തിരയുക',language:'ഭാഷ',profile:'പ്രൊഫൈൽ',
    lookupByCode:'ഉപഭോക്തൃ ID കൊണ്ട് തിരയുക',lookup:'തിരയുക',deleteCustomer:'ഇല്ലാതാക്കുക',remind:'ഓർമ്മപ്പെടുത്തുക',
    reminders:'ബാലൻസ് ഓർമ്മപ്പെടുത്തലുകൾ',fromContacts:'കോൺടാക്റ്റുകളിൽ നിന്ന്',phoneOnly:'ഫോൺ മാത്രം',priceCompare:'വില താരതമ്യം',
    stock:'സ്റ്റോക്ക്',bills:'ബില്ലുകൾ',saveCustomer:'ഉപഭോക്താവിനെ സേവ് ചെയ്യുക',cancel:'റദ്ദാക്കുക'
  },
};
const languageLocales={en:'en-IN',hi:'hi-IN',bn:'bn-IN',mr:'mr-IN',te:'te-IN',kn:'kn-IN',ta:'ta-IN',or:'or-IN',ml:'ml-IN'};
let currentLanguage='en';
let currentSection='dashboard';
function t(key){
  return translations[currentLanguage][key]||translations.en[key]||key;
}
function updateSectionTitle(){
  const key=currentSection==='addCustomer'
    ?editingCustomerId?'editCustomerTitle':'addCustomerTitle'
    :({inventory:'stock',report:'reportTitle'}[currentSection]||currentSection);
  title.textContent=t(key);
  if(currentSection==='addCustomer'){
    document.getElementById('customerFormTitle').textContent=t(key);
    document.getElementById('saveCustomerButton').textContent=t(editingCustomerId?'updateCustomer':'saveCustomer');
    document.getElementById('cancelCustomerEdit').textContent=t('cancel');
  }
}
function applyLanguage(language){
  currentLanguage=translations[language]?language:'en';
  document.documentElement.lang=languageLocales[currentLanguage];
  document.querySelectorAll('[data-i18n]').forEach(element=>{element.textContent=t(element.dataset.i18n);});
  document.querySelectorAll('[data-i18n-placeholder]').forEach(element=>{element.placeholder=t(element.dataset.i18nPlaceholder);});
  document.querySelectorAll('[data-i18n-aria-label]').forEach(element=>{element.setAttribute('aria-label',t(element.dataset.i18nAriaLabel));});
  document.querySelectorAll('.bill-status').forEach(element=>{element.textContent=t(element.dataset.status);});
  document.querySelectorAll('.language-option').forEach(option=>{
    option.setAttribute('aria-pressed',String(option.dataset.language===currentLanguage));
  });
  document.getElementById('languageSelectedLabel').textContent=
    document.querySelector(`.language-option[data-language="${currentLanguage}"]`).textContent;
  currencyFormatter=new Intl.NumberFormat(languageLocales[currentLanguage],{style:'currency',currency:'INR',maximumFractionDigits:2});
  const selectedCredit=document.querySelector('.credit-option[aria-pressed="true"]');
  document.getElementById('customerAmountLabel').textContent=t(selectedCredit.dataset.type==='given'?'amountGiven':'amountTaken');
  updateSectionTitle();
  renderCustomers();
  renderInv(inventoryItems);
}
function showSection(id){
  currentSection=id;
  sections.forEach(section=>section.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  updateSectionTitle();
  document.getElementById('addCustomerButton').style.display=(id==='dashboard')?'grid':'none';
  const activeView=id==='profile'||id==='addCustomer'?'dashboard':id==='report'?'bills':id;
  views.forEach(view=>{
    const isActive=view.dataset.view===activeView;
    view.classList.toggle('active',isActive);
    if(isActive) view.setAttribute('aria-current','page');
    else view.removeAttribute('aria-current');
  });
}
views.forEach(a=>a.addEventListener('click',e=>{e.preventDefault();showSection(a.dataset.view);}));
document.getElementById('viewReportButton').addEventListener('click',()=>showSection('report'));
document.getElementById('backToBillsButton').addEventListener('click',()=>showSection('bills'));
/* customers come from backend API */
let snapshot=null;
let voiceBusy=false;
let recorder=null;
let sttLanguage='hi-IN,en-IN';
const customerList=document.getElementById('customerList');
const customerNotice=document.getElementById('customerNotice');
const customerForm=document.getElementById('customerForm');
const customerFormNotice=document.getElementById('customerFormNotice');
let currencyFormatter=new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:2});
let customers=[];
let customerStorageReady=true;
let editingCustomerId=null;
function isCustomerRecord(customer){
  return customer!==null
    && typeof customer==='object'
    && typeof customer.id==='string'
    && typeof customer.name==='string'
    && typeof customer.phone==='string'
    && (customer.type==='given'||customer.type==='taken')
    && typeof customer.amount==='number'
    && Number.isFinite(customer.amount)
    && customer.amount>0
    && typeof customer.date==='string'
    && !Number.isNaN(Date.parse(customer.date));
}
function setNotice(element,message,isError){
  element.textContent=message;
  element.hidden=!message;
  element.classList.toggle('error',Boolean(isError));
}
function formatCustomerDate(value){
  return new Date(value).toLocaleString(languageLocales[currentLanguage],{dateStyle:'medium',timeStyle:'short'});
}
function reminderStatusFor(customerId){
  const reminder=getReminderForCustomer(customerId);
  if(!reminder) return {key:'reminderOff', active:false, sent:false};
  if(reminder.status==='sent') return {key:'reminderSent', active:false, sent:true, dueAt:reminder.dueAt};
  return {key:'reminderOn', active:true, sent:false, dueAt:reminder.dueAt};
}

function renderCustomers(){
  customerList.replaceChildren();
  const creditGiven=customers.reduce((total,customer)=>total+Math.max(0, Number(customer.balance_rupees ?? customer.amount) || 0),0);
  const creditTaken=snapshot?.summary ? (Number(snapshot.summary.total_payment_paise)||0)/100 : customers.filter(c=>c.type==='taken').reduce((t,c)=>t+c.amount,0);
  document.getElementById('totalCreditGiven').textContent=currencyFormatter.format(creditGiven);
  document.getElementById('totalCreditTaken').textContent=currencyFormatter.format(creditTaken);
  const searchTerm=document.getElementById('customerSearch').value.trim().toLocaleLowerCase(languageLocales[currentLanguage]);
  const visibleCustomers=customers.filter(customer=>
    `${customer.name} ${customer.phone} ${customer.code||''}`.toLocaleLowerCase(languageLocales[currentLanguage]).includes(searchTerm),
  );
  if(visibleCustomers.length===0){
    const emptyState=document.createElement('p');
    emptyState.className='empty-state';
    emptyState.textContent=customers.length===0?t('noCustomers'):t('noCustomerMatches');
    customerList.append(emptyState);
    return;
  }
  visibleCustomers.forEach(customer=>{
    const status=reminderStatusFor(customer.id);
    const row=document.createElement('div');
    row.className='customer-row';
    row.dataset.customerId=customer.id;
    const details=document.createElement('button');
    details.type='button';
    details.className='customer-row-main';
    details.setAttribute('aria-label',`${customer.name}, ${customer.code||''}, ${currencyFormatter.format(Number(customer.balance_rupees ?? customer.amount) || 0)}`);
    const name=document.createElement('h3');
    name.textContent=customer.name || customer.phone || t('customer');
    const meta=document.createElement('p');
    meta.className='customer-meta';
    meta.textContent=`${customer.code || '—'} · ${customer.phone || '—'}`;
    const reminderLine=document.createElement('p');
    reminderLine.className=`customer-reminder${status.active?' is-on':''}${status.sent?' is-sent':''}`;
    reminderLine.textContent=status.active && status.dueAt
      ? `${t(status.key)} · ${formatCustomerDate(status.dueAt)}`
      : t(status.key);
    details.append(name,meta,reminderLine);
    const right=document.createElement('div');
    right.className='customer-row-side';
    const amount=document.createElement('div');
    amount.className='customer-amount';
    amount.textContent=currencyFormatter.format(Number(customer.balance_rupees ?? customer.amount) || 0);
    const actions=document.createElement('div');
    actions.className='customer-row-actions';
    const remindBtn=document.createElement('button');
    remindBtn.type='button';
    remindBtn.className='row-action remind';
    remindBtn.dataset.action='remind';
    remindBtn.dataset.customerId=customer.id;
    remindBtn.textContent=status.active?t('reminderOn'):t('remind');
    const deleteBtn=document.createElement('button');
    deleteBtn.type='button';
    deleteBtn.className='row-action delete';
    deleteBtn.dataset.action='delete';
    deleteBtn.dataset.customerId=customer.id;
    deleteBtn.textContent=t('deleteCustomer');
    actions.append(remindBtn,deleteBtn);
    right.append(amount,actions);
    row.append(details,right);
    details.addEventListener('click',()=>startCustomerEdit(customer.id));
    customerList.append(row);
  });
}
/* customers loaded from API via refreshFromBackend() */

function getLocalDateTime(){
  const now=new Date();
  now.setMinutes(now.getMinutes()-now.getTimezoneOffset());
  return now.toISOString().slice(0,16);
}
function setCreditType(type){
  document.querySelectorAll('.credit-option').forEach(button=>{
    button.setAttribute('aria-pressed',String(button.dataset.type===type));
  });
  document.getElementById('customerAmountLabel').textContent=t(type==='given'?'amountGiven':'amountTaken');
}
function resetCustomerForm(){
  editingCustomerId=null;
  customerForm.reset();
  document.getElementById('customerDate').value=getLocalDateTime();
  document.getElementById('cancelCustomerEdit').hidden=true;
  setNotice(customerFormNotice,'',false);
  setCreditType('given');
  const hist=document.getElementById('customerTxnHistory');
  if(hist) hist.hidden=true;
  const list=document.getElementById('customerTxnList');
  if(list) list.replaceChildren();
  updateSectionTitle();
}
function beginNewCustomer(){
  resetCustomerForm();
  document.getElementById('cancelCustomerEdit').hidden=false;
  showSection('addCustomer');
}
async function loadCustomerTransactions(customerId){
  const hist=document.getElementById('customerTxnHistory');
  const list=document.getElementById('customerTxnList');
  if(!hist||!list) return;
  hist.hidden=false;
  list.replaceChildren();
  try{
    await ensureAuth();
    const txns=await listTransactions(customerId, 12);
    if(!txns.length){
      const empty=document.createElement('li');
      empty.textContent=t('noRecent');
      list.append(empty);
      return;
    }
    txns.forEach(txn=>{
      const li=document.createElement('li');
      const left=document.createElement('div');
      left.innerHTML=`<strong>${txn.type}</strong><div class="recent-meta">${txn.txn_date}</div>`;
      const right=document.createElement('div');
      right.textContent=currencyFormatter.format(Number(txn.amount_rupees)||0);
      li.append(left,right);
      list.append(li);
    });
  }catch(err){
    const empty=document.createElement('li');
    empty.textContent=err.message;
    list.append(empty);
  }
}
function startCustomerEdit(id){
  const customer=customers.find(entry=>entry.id===id);
  if(!customer){
    setNotice(customerNotice,t('customerMissing'),true);
    return;
  }
  editingCustomerId=customer.id;
  document.getElementById('customerName').value=customer.name;
  document.getElementById('customerPhone').value=customer.phone;
  document.getElementById('customerAmount').value=String(customer.amount);
  document.getElementById('customerDate').value=customer.date;
  document.getElementById('cancelCustomerEdit').hidden=false;
  setNotice(customerFormNotice,'',false);
  setCreditType(customer.type);
  updateSectionTitle();
  showSection('addCustomer');
  loadCustomerTransactions(customer.id);
}
document.getElementById('addCustomerButton').addEventListener('click',beginNewCustomer);
document.getElementById('customersAddButton').addEventListener('click',beginNewCustomer);
const voiceButton=document.querySelector('.voice-button');
const voiceInstruction=document.querySelector('.voice-instruction');
voiceButton.querySelectorAll('.loader-block').forEach((block,index)=>{
  block.style.animationDelay=`${index*0.12}s`;
});
function setVoiceStatus(text){
  if(voiceInstruction) voiceInstruction.textContent=text;
}
async function playReply(text){
  if(!text) return;
  let played=false;
  try{
    await Promise.race([
      speakText(text,'hi-en').then(()=>{played=true;}),
      new Promise((_,reject)=>setTimeout(()=>reject(new Error('tts timeout')),4000)),
    ]);
  }catch{}
  if(!played) speak(text);
}
voiceButton.addEventListener('click',async ()=>{
  if(voiceBusy) return;
  if(!isRecordingSupported()){
    setVoiceStatus('Microphone is not supported in this browser.');
    return;
  }
  const listening=voiceButton.getAttribute('aria-pressed')==='true';
  if(!listening){
    try{
      stopSpeaking();
      recorder=new VoiceRecorder();
      await recorder.start();
      voiceButton.setAttribute('aria-pressed','true');
      voiceButton.classList.add('listening');
      setVoiceStatus('Sun raha hoon… phir se dabaiye to bhejein');
    }catch(err){
      setVoiceStatus(`Mic permission chahiye: ${err.message}`);
    }
    return;
  }
  voiceBusy=true;
  voiceButton.setAttribute('aria-pressed','false');
  voiceButton.classList.remove('listening');
  setVoiceStatus('Process ho raha hai…');
  try{
    const wav=await recorder?.stop();
    recorder=null;
    if(!wav) throw new Error('Koi audio capture nahi hua');
    await ensureAuth();
    const result=await sendAudio(wav, sttLanguage);
    const reply=result.reply_text || 'Ho gaya.';
    setVoiceStatus(result.transcript ? `Suna: ${result.transcript} — ${reply}` : reply);
    await playReply(reply);
    // Persist + refresh list so newly voice-added customers appear immediately
    await refreshFromBackend();
    if(result?.customer?.id && !customers.some(c=>String(c.id)===String(result.customer.id))){
      customers=[...customers,{
        id:String(result.customer.id),
        name:result.customer.name||'',
        phone:'',
        type:'given',
        amount:0.01,
        balance_rupees:Number(result.customer.balance_rupees)||0,
        date:new Date().toISOString().slice(0,16),
        code:result.customer.code||'',
      }];
      renderCustomers();
    }
  }catch(err){
    setVoiceStatus(err.message || 'Voice command failed');
  }finally{
    voiceBusy=false;
  }
});
document.getElementById('cancelCustomerEdit').addEventListener('click',()=>{
  resetCustomerForm();
  showSection('customers');
});
document.getElementById('customerSearch').addEventListener('input',renderCustomers);
document.getElementById('customerSearchForm').addEventListener('submit',event=>{
  event.preventDefault();
  renderCustomers();
});
customerList.addEventListener('click',async event=>{
  const actionBtn=event.target.closest('[data-action]');
  if(actionBtn){
    event.preventDefault();
    const id=actionBtn.dataset.customerId;
    const customer=customers.find(entry=>entry.id===id);
    if(!customer) return;
    if(actionBtn.dataset.action==='delete'){
      if(!window.confirm(t('confirmDelete'))) return;
      try{
        await ensureAuth();
        await archiveCustomer(id);
        setNotice(customerNotice,t('customerDeleted'),false);
        await refreshFromBackend();
      }catch(err){
        setNotice(customerNotice,err.message,true);
      }
      return;
    }
    if(actionBtn.dataset.action==='remind'){
      addReminder({
        customerId:customer.id,
        customerName:customer.name,
        phone:customer.phone,
        balanceRupees:customer.balance_rupees ?? customer.amount,
        dueAt:defaultDueInDays(3),
        note:`Balance due reminder for ${customer.code||customer.name}`,
      });
      setNotice(customerNotice,t('remindScheduled'),false);
      renderCustomers();
    }
    return;
  }
});
document.getElementById('customerDate').value=getLocalDateTime();
customerForm.addEventListener('submit',async event=>{
  event.preventDefault();
  if(editingCustomerId&&!customers.some(entry=>entry.id===editingCustomerId)){
    setNotice(customerFormNotice,t('customerMissing'),true);
    return;
  }
  const selectedCredit=document.querySelector('.credit-option[aria-pressed="true"]');
  const name=document.getElementById('customerName').value.trim();
  const phone=document.getElementById('customerPhone').value.trim();
  const amount=Number(document.getElementById('customerAmount').value);
  const dateValue=document.getElementById('customerDate').value;
  const type=selectedCredit.dataset.type;
  if(!phone){
    setNotice(customerFormNotice,t('invalidCustomer'),true);
    return;
  }
  const resolvedName=name || `Customer ${phone.slice(-4)}`;
  const saveBtn=document.getElementById('saveCustomerButton');
  saveBtn.disabled=true;
  try{
    await ensureAuth();
    if(editingCustomerId){
      const updated=await updateCustomer(editingCustomerId,{name:resolvedName, phone});
      if(updated?.customer_code){
        setNotice(document.getElementById('registeredCodeNotice'), `${t('idUpdated')}: ${updated.customer_code}`, false);
      }
    }else{
      const created=await createCustomer({name:resolvedName, phone});
      setNotice(document.getElementById('registeredCodeNotice'), `${t('registeredCode')}: ${created.customer_code}`, false);
      if(amount>0){
        const txnType=type==='taken'?'payment':'credit';
        const txnDate=(dateValue || getLocalDateTime()).slice(0,10);
        await createTransaction({
          customerId:created.id,
          type:txnType,
          amountRupees:amount,
          txnDate,
          idempotencyKey:`ui-${created.id}-${txnType}-${amount}-${txnDate}-${Date.now()}`,
        });
      }
    }
    resetCustomerForm();
    document.getElementById('customerSearch').value='';
    setNotice(customerNotice,'',false);
    await refreshFromBackend();
    showSection('customers');
  }catch(error){
    setNotice(customerFormNotice,error.message||t('customerStorageSaveError'),true);
    console.error('Unable to save customer:',error);
  }finally{
    saveBtn.disabled=false;
  }
});
document.querySelectorAll('.credit-option').forEach(button=>button.addEventListener('click',()=>setCreditType(button.dataset.type)));
const tabSales=document.getElementById('tabSales'),tabPurch=document.getElementById('tabPurch');
tabSales.addEventListener('click',()=>{tabSales.classList.remove('secondary');tabPurch.classList.add('secondary');tabSales.setAttribute('aria-selected','true');tabPurch.setAttribute('aria-selected','false');document.getElementById('salesCard').style.display='block';document.getElementById('purchCard').style.display='none';});
tabPurch.addEventListener('click',()=>{tabPurch.classList.remove('secondary');tabSales.classList.add('secondary');tabPurch.setAttribute('aria-selected','true');tabSales.setAttribute('aria-selected','false');document.getElementById('salesCard').style.display='none';document.getElementById('purchCard').style.display='block';});
let inventoryItems=[];
let quoteCatalog=[];
const it=document.getElementById('invTable');
function normalizeStockItem(i){
  return {
    ...i,
    reorder_level:Number(i.minimum_quantity ?? i.reorder_level ?? 5),
    unit_cost_rupees:Number(i.unit_price_rupees ?? i.unit_cost_rupees ?? 0),
    low_stock:Boolean(i.low_stock ?? (Number(i.quantity)<=Number(i.minimum_quantity ?? i.reorder_level ?? 5))),
  };
}
function renderInv(list){
  if(!it) return;
  it.replaceChildren();
  const fragment=document.createDocumentFragment();
  (list||[]).forEach(i=>{
    const qty=Number(i.quantity ?? i.stock ?? 0);
    const reorder=Number(i.reorder_level ?? i.minimum_quantity ?? 10);
    const status=qty===0?'overdue':qty<=reorder?'pending':'paid';
    const label=qty===0?t('stockOut'):qty<=reorder?t('stockLow'):t('inStock');
    const tr=document.createElement('tr');
    tr.dataset.itemId=i.id||'';
    tr.style.cursor='pointer';
    const nameTd=document.createElement('td');nameTd.textContent=i.name;
    const stockTd=document.createElement('td');stockTd.textContent=String(qty);
    const priceTd=document.createElement('td');priceTd.textContent=`₹${Number(i.unit_cost_rupees ?? i.unit_price_rupees ?? i.price ?? 0).toFixed(0)}`;
    const statusTd=document.createElement('td');
    const badge=document.createElement('span');badge.className=`badge ${status}`;badge.textContent=label;
    statusTd.append(badge);
    tr.append(nameTd,stockTd,priceTd,statusTd);
    tr.addEventListener('click',()=>onStockRowClick(i));
    fragment.append(tr);
  });
  it.append(fragment);
}
document.getElementById('invSearch')?.addEventListener('input',e=>{
  const q=e.target.value.toLowerCase();
  renderInv(inventoryItems.filter(i=>i.name.toLowerCase().includes(q)));
});
document.getElementById('addInventoryButton')?.addEventListener('click',async ()=>{
  const name=window.prompt(t('addStockPrompt'));
  if(!name) return;
  const qtyRaw=window.prompt(t('stockQtyPrompt'),'10');
  const quantity=Math.max(0, Number(qtyRaw)||0);
  try{
    await ensureAuth();
    await createStockItem({name, quantity, minimum_quantity:5, unit_price_rupees:0, category:'general'});
    setNotice(document.getElementById('inventoryNotice'),t('stockAdded'),false);
    await refreshInventory();
  }catch(err){
    setNotice(document.getElementById('inventoryNotice'),err.message,true);
  }
});
async function onStockRowClick(item){
  if(!item?.id) return;
  const action=window.prompt('Stock action: add / remove / quotes','quotes');
  if(!action) return;
  const mode=action.trim().toLowerCase();
  try{
    await ensureAuth();
    if(mode==='add'){
      const qty=Math.max(1, Number(window.prompt(t('stockQtyPrompt'),'5'))||0);
      await addStock(item.id, qty, 'restock');
      setNotice(document.getElementById('inventoryNotice'),`Added ${qty} to ${item.name}`,false);
      await refreshInventory();
      return;
    }
    if(mode==='remove'){
      const qty=Math.max(1, Number(window.prompt(t('stockQtyPrompt'),'1'))||0);
      await removeStock(item.id, qty, 'sold');
      setNotice(document.getElementById('inventoryNotice'),`Removed ${qty} from ${item.name}`,false);
      await refreshInventory();
      return;
    }
    await loadQuotesForItem(item.id);
  }catch(err){
    setNotice(document.getElementById('inventoryNotice'),err.message,true);
  }
}
const languageDropdown=document.getElementById('languageDropdown');
const languageNotice=document.getElementById('languageNotice');
let savedLanguage='en';
let languageLoadFailed=false;
try{
  const storedLanguage=localStorage.getItem('voiceKhata.language');
  if(translations[storedLanguage]) savedLanguage=storedLanguage;
}catch(error){
  languageLoadFailed=true;
  console.error('Unable to load language preference:',error);
}
applyLanguage(savedLanguage);
if(languageLoadFailed) setNotice(languageNotice,t('languageLoadError'),true);
document.querySelectorAll('.language-option').forEach(option=>option.addEventListener('click',()=>{
  applyLanguage(option.dataset.language);
  languageDropdown.open=false;
  try{
    localStorage.setItem('voiceKhata.language',currentLanguage);
    setNotice(languageNotice,'',false);
  }catch(error){
    setNotice(languageNotice,t('languageSaveError'),true);
    console.error('Unable to save language preference:',error);
  }
}));
const billsFull=[{no:'VK-1042',date:'21 Nov',cust:'Anita Sharma',amt:'₹2,340',status:'paid'},{no:'VK-1041',date:'20 Nov',cust:'Rajesh Patil',amt:'₹1,120',status:'pending'}];
const purchFull=[{no:'VK-P218',date:'19 Nov',vendor:'Sharma Traders',amt:'₹8,450',status:'paid'},{no:'VK-P217',date:'17 Nov',vendor:'City Wholesale',amt:'₹3,280',status:'pending'}];
const bt=document.getElementById('billsTable');
const pt=document.getElementById('purchTable');
function renderBillRows(table,list,partyKey){
  table.replaceChildren();
  const fragment=document.createDocumentFragment();
  list.forEach(b=>{
    const tr=document.createElement('tr');
    const noTd=document.createElement('td');noTd.textContent=b.no;
    const dateTd=document.createElement('td');dateTd.textContent=b.date;
    const partyTd=document.createElement('td');partyTd.textContent=b[partyKey];
    const amtTd=document.createElement('td');amtTd.textContent=b.amt;
    const statusTd=document.createElement('td');
    const badge=document.createElement('span');badge.className=`badge ${b.status} bill-status`;badge.dataset.status=b.status;badge.textContent=t(b.status);
    statusTd.append(badge);
    tr.append(noTd,dateTd,partyTd,amtTd,statusTd);
    fragment.append(tr);
  });
  table.append(fragment);
}
function filterBills(list,query,partyKey){
  const q=query.trim().toLowerCase();
  if(!q) return list;
  return list.filter(b=>`${b.no} ${b.date} ${b[partyKey]} ${b.amt} ${b.status}`.toLowerCase().includes(q));
}
function renderSalesBills(){
  renderBillRows(bt,filterBills(billsFull,document.getElementById('salesSearch').value,'cust'),'cust');
}
function renderPurchBills(){
  renderBillRows(pt,filterBills(purchFull,document.getElementById('purchSearch').value,'vendor'),'vendor');
}
renderSalesBills();
renderPurchBills();
document.getElementById('salesSearch').addEventListener('input',renderSalesBills);
document.getElementById('purchSearch').addEventListener('input',renderPurchBills);
document.getElementById('addSalesBillButton').addEventListener('click',()=>document.getElementById('salesFile').click());
document.getElementById('addPurchBillButton').addEventListener('click',()=>document.getElementById('purchFile').click());


function renderRecentActivity(recent){
  const list=document.getElementById('recentActivity');
  if(!list) return;
  list.replaceChildren();
  if(!recent?.length){
    const li=document.createElement('li');
    li.textContent=t('noRecent');
    list.append(li);
    return;
  }
  recent.slice(0,4).forEach(item=>{
    const li=document.createElement('li');
    const left=document.createElement('div');
    left.innerHTML=`<strong>${item.customer}</strong><div class="recent-meta">${item.type} · ${item.status}</div>`;
    const right=document.createElement('div');
    right.textContent=currencyFormatter.format(Number(item.amount_rupees)||0);
    li.append(left,right);
    list.append(li);
  });
}

function updateDashboardSnapshot(state, stockSummary){
  const summary=state?.summary||{};
  const todayCredit=document.getElementById('todayCredit');
  const todayPayments=document.getElementById('todayPayments');
  const lowStockEl=document.getElementById('lowStockCount');
  if(todayCredit) todayCredit.textContent=currencyFormatter.format((Number(summary.total_credit_paise)||0)/100);
  if(todayPayments) todayPayments.textContent=currencyFormatter.format((Number(summary.total_payment_paise)||0)/100);
  const lowCount=typeof stockSummary?.low_stock_count==='number'
    ? stockSummary.low_stock_count
    : inventoryItems.filter(i=>Number(i.quantity)<=Number(i.reorder_level ?? i.minimum_quantity ?? 5)).length;
  if(lowStockEl) lowStockEl.textContent=String(lowCount);
}

async function refreshInventory(){
  const [stockListed, quoteListed] = await Promise.all([
    listStock(),
    listInventory().catch(()=>({items:[]})),
  ]);
  inventoryItems=(Array.isArray(stockListed)?stockListed:[]).map(normalizeStockItem);
  quoteCatalog=quoteListed.items||[];
  renderInv(inventoryItems);
  await renderPriceCompareFromApi(inventoryItems.filter(i=>i.low_stock).slice(0,5));
  return {items:inventoryItems, low_stock_count:inventoryItems.filter(i=>i.low_stock).length};
}

function quoteIdForStockItem(item){
  const match=quoteCatalog.find(q=>String(q.name).toLowerCase()===String(item.name).toLowerCase());
  return match?.id || null;
}

async function renderPriceCompareFromApi(items){
  const body=document.getElementById('priceCompareBody');
  if(!body) return;
  body.replaceChildren();
  const targets=items?.length?items:inventoryItems.slice(0,5);
  for(const item of targets){
    const quoteId=quoteIdForStockItem(item);
    if(!quoteId) continue;
    try{
      const data=await getItemQuotes(quoteId);
      const bySource=Object.fromEntries((data.quotes||[]).map(q=>[q.source, q.price_rupees]));
      const tr=document.createElement('tr');
      const best=data.best_source?`${sourceLabel(data.best_source)} ₹${Number(data.best_price_rupees).toFixed(0)}`:'—';
      [
        item.name,
        `₹${Number(item.unit_cost_rupees||item.unit_price_rupees||0).toFixed(0)}`,
        bySource.jumbotail!=null?`₹${Number(bySource.jumbotail).toFixed(0)}`:'—',
        bySource.flipkart!=null?`₹${Number(bySource.flipkart).toFixed(0)}`:'—',
        bySource.amazon!=null?`₹${Number(bySource.amazon).toFixed(0)}`:'—',
        best,
      ].forEach((value,index)=>{
        const td=document.createElement('td');
        td.textContent=value;
        if(index===5) td.className='price-best';
        tr.append(td);
      });
      body.append(tr);
    }catch{
      /* skip item without quotes */
    }
  }
}

async function loadQuotesForItem(itemId){
  if(!itemId) return;
  const item=inventoryItems.find(i=>String(i.id)===String(itemId));
  if(item) await renderPriceCompareFromApi([item]);
}

async function refreshFromBackend(){
  try{
    await ensureAuth();
    const [state, listed, stockListed, stockSummary, quoteListed] = await Promise.all([
      getState(),
      listCustomers(),
      listStock(),
      getStockSummary(),
      listInventory().catch(()=>({items:[]})),
    ]);
    snapshot = state;
    inventoryItems = (Array.isArray(stockListed)?stockListed:[]).map(normalizeStockItem);
    quoteCatalog = quoteListed.items||[];
    const balances = new Map((state.customers||[]).map(c=>[String(c.id), c]));
    customers = (listed.items||[]).map(c=>{
      const bal = balances.get(String(c.id));
      const balanceRupees = bal ? Number(bal.balance_rupees)||0 : 0;
      return {
        id:String(c.id),
        name:c.name||'',
        phone:c.phone||'',
        type: balanceRupees >= 0 ? 'given' : 'taken',
        amount: Math.max(0.01, Math.abs(balanceRupees)),
        balance_rupees: balanceRupees,
        date:(c.created_at||new Date().toISOString()).slice(0,16),
        code:c.customer_code||'',
      };
    });
    if(customers.length===0 && (state.customers||[]).length){
      customers = state.customers.map(c=>({
        id:String(c.id),
        name:c.name||'',
        phone:'',
        type:'given',
        amount:Math.max(0.01, Math.abs(Number(c.balance_rupees)||0)),
        balance_rupees:Number(c.balance_rupees)||0,
        date:new Date().toISOString().slice(0,16),
        code:c.code||'',
      }));
    }
    renderCustomers();
    renderInv(inventoryItems);
    updateReportsFromSummary(state.summary);
    updateDashboardSnapshot(state, stockSummary);
    renderRecentActivity(state.recent||[]);
    await renderPriceCompareFromApi(inventoryItems.filter(i=>i.low_stock).slice(0,5));
  }catch(error){
    setNotice(customerNotice, `Backend: ${error.message}`, true);
    console.error(error);
  }
}

function updateReportsFromSummary(summary){
  if(!summary) return;
  const credit=(Number(summary.total_credit_paise)||0)/100;
  const payment=(Number(summary.total_payment_paise)||0)/100;
  const net=(Number(summary.net_paise)||0)/100;
  const line=`Today credit ${currencyFormatter.format(credit)} · Payments ${currencyFormatter.format(payment)} · Net ${currencyFormatter.format(net)}`;
  const reportsLine=document.querySelector('[data-i18n="reportsLine"]');
  if(reportsLine) reportsLine.textContent=line;
}

const originalApplyLanguage=applyLanguage;
applyLanguage=function(language){
  originalApplyLanguage(language);
  const map={en:'en-IN',hi:'hi-IN,en-IN',bn:'bn-IN,en-IN',mr:'mr-IN,en-IN',te:'te-IN,en-IN',kn:'kn-IN,en-IN',ta:'ta-IN,en-IN',or:'or-IN,en-IN',ml:'ml-IN,en-IN'};
  sttLanguage=map[currentLanguage]||'hi-IN,en-IN';
};



async function lookupCustomerCode(event){
  event.preventDefault();
  const input=document.getElementById('customerCodeInput');
  const notice=document.getElementById('codeLookupNotice');
  const code=(input.value||'').trim();
  if(!code){
    setNotice(notice,t('invalidCustomer'),true);
    return;
  }
  try{
    await ensureAuth();
    const customer=await getCustomerByCode(code);
    let bal=0;
    try{
      const balance=await getBalance(customer.id);
      bal=Number(balance.balance_rupees)||0;
    }catch{}
    setNotice(notice,`${customer.name} · ${customer.customer_code} · ${currencyFormatter.format(bal)}`,false);
    setVoiceStatus(`${customer.name} (${customer.customer_code}) — ${currencyFormatter.format(bal)}`);
    document.getElementById('customerSearch').value=customer.customer_code;
    showSection('customers');
    renderCustomers();
  }catch(err){
    setNotice(notice,err.message,true);
  }
}
document.getElementById('customerCodeLookup')?.addEventListener('submit',lookupCustomerCode);

document.getElementById('pickContactButton')?.addEventListener('click',async ()=>{
  const notice=document.getElementById('customerFormNotice');
  try{
    if(!('contacts' in navigator && 'ContactsManager' in window)){
      setNotice(notice,t('contactsUnsupported'),true);
      return;
    }
    const contacts=await navigator.contacts.select(['name','tel'],{multiple:false});
    const contact=contacts?.[0];
    if(!contact) return;
    const name=(contact.name&&contact.name[0])||'';
    const phone=(contact.tel&&contact.tel[0])||'';
    document.getElementById('customerName').value=name;
    document.getElementById('customerPhone').value=phone;
    setNotice(notice,'',false);
  }catch(err){
    setNotice(notice,t('contactsDenied'),true);
  }
});

document.getElementById('phoneOnlyToggle')?.addEventListener('click',()=>{
  const nameInput=document.getElementById('customerName');
  nameInput.value='';
  nameInput.removeAttribute('required');
  setNotice(document.getElementById('customerFormNotice'),t('phoneOnlyHint'),false);
  document.getElementById('customerPhone').focus();
});

document.getElementById('refreshQuotes')?.addEventListener('click',async ()=>{
  try{
    await ensureAuth();
    await renderPriceCompareFromApi(inventoryItems.filter(i=>i.low_stock).slice(0,5));
  }catch(err){
    setNotice(document.getElementById('inventoryNotice'),err.message,true);
  }
});

(async function boot(){
  setVoiceStatus(isRecordingSupported() ? 'Bolne ke liye dabaiye' : 'Mic unavailable — use Add customer');
  try{
    await healthCheck();
    await mountAuthGate({ root: document.body });
    mountWelcome({
      root:document.body,
      initialLanguage:currentLanguage,
      onContinue:(language)=>{
        applyLanguage(language);
        try{localStorage.setItem('voiceKhata.language',language);}catch{}
      },
    });
    const profileCard=document.querySelector('#profile .profile');
    if(profileCard){
      const email=getShopEmail();
      let emailLine=document.getElementById('shopEmailLine');
      if(!emailLine){
        emailLine=document.createElement('p');
        emailLine.id='shopEmailLine';
        emailLine.style.cssText='color:var(--muted);font-size:13px;margin:0 0 8px';
        profileCard.insertBefore(emailLine, profileCard.children[2] || null);
      }
      emailLine.textContent=email?`Signed in as ${email}`:'';
      if(!document.getElementById('signOutButton')){
        const signOutBtn=document.createElement('button');
        signOutBtn.type='button';
        signOutBtn.id='signOutButton';
        signOutBtn.className='secondary';
        signOutBtn.textContent='Sign out';
        signOutBtn.addEventListener('click',()=>{
          clearShopSession();
          window.location.reload();
        });
        profileCard.append(signOutBtn);
      }
    }
    await refreshFromBackend();
  }catch(err){
    setVoiceStatus(`Backend offline: ${err.message}`);
    setNotice(customerNotice, `Backend se connect nahi hua: ${err.message}`, true);
  }
})();
