export const RESERVATION_DURATIONS = Array.from({ length: 8 }, (_, index) => (index + 1) * 30);

export function formatDuration(minutes) {
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  if (hours === 0) return `${minutes} minutos`;
  const hourLabel = `${hours} ${hours === 1 ? 'hora' : 'horas'}`;
  return remainingMinutes ? `${hourLabel} y ${remainingMinutes} minutos` : hourLabel;
}

function formatDate(date) {
  return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, '0')}-${String(date.getUTCDate()).padStart(2, '0')}`;
}

export function addDuration(date, time, durationMinutes) {
  if (!date || !time || !Number.isInteger(Number(durationMinutes))) return null;
  const [hour, minute] = time.split(':').map(Number);
  const totalMinutes = hour * 60 + minute + Number(durationMinutes);
  const endDate = new Date(`${date}T00:00:00Z`);
  endDate.setUTCDate(endDate.getUTCDate() + Math.floor(totalMinutes / 1440));
  const normalizedMinutes = totalMinutes % 1440;
  return {
    date: formatDate(endDate),
    time: `${String(Math.floor(normalizedMinutes / 60)).padStart(2, '0')}:${String(normalizedMinutes % 60).padStart(2, '0')}`,
  };
}

export function durationBetween(start, end) {
  if (!start || !end) return 30;
  const difference = (new Date(end).getTime() - new Date(start).getTime()) / 60000;
  return Number.isInteger(difference) && difference > 0 ? difference : 30;
}
