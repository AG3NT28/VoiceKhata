const STORAGE_KEY = 'voicekhata.reminders';

function load() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function save(items) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
}

export function listReminders() {
  return load().sort((a, b) => String(a.dueAt).localeCompare(String(b.dueAt)));
}

/** Latest active (or most recent) reminder for a customer. */
export function getReminderForCustomer(customerId) {
  const id = String(customerId);
  const items = listReminders().filter((item) => String(item.customerId) === id);
  if (!items.length) return null;
  const scheduled = items.find((item) => item.status === 'scheduled');
  return scheduled || items[items.length - 1];
}

export function addReminder({ customerId, customerName, phone, balanceRupees, dueAt, note }) {
  const items = load().filter(
    (item) => !(String(item.customerId) === String(customerId) && item.status === 'scheduled'),
  );
  const reminder = {
    id: `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
    customerId,
    customerName,
    phone: phone || '',
    balanceRupees: Number(balanceRupees) || 0,
    dueAt,
    note: note || '',
    status: 'scheduled',
    createdAt: new Date().toISOString(),
  };
  items.push(reminder);
  save(items);
  return reminder;
}

export function markReminderSent(id) {
  const items = load().map((item) =>
    item.id === id
      ? { ...item, status: 'sent', sentAt: new Date().toISOString() }
      : item,
  );
  save(items);
  return items.find((item) => item.id === id);
}

export function deleteReminder(id) {
  save(load().filter((item) => item.id !== id));
}

/** Reminders due within the next N days (default 3). */
export function dueSoon(days = 3) {
  const now = Date.now();
  const horizon = now + days * 24 * 60 * 60 * 1000;
  return listReminders().filter((item) => {
    if (item.status === 'sent') return false;
    const due = Date.parse(item.dueAt);
    return Number.isFinite(due) && due <= horizon;
  });
}

export function defaultDueInDays(days = 3) {
  const d = new Date();
  d.setDate(d.getDate() + days);
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}
