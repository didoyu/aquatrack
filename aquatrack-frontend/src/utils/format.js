export const fmt = (n, d = 1) => (n == null ? "-" : Number(n).toFixed(d));
export const peso = (n) => (n == null ? "-" : "₱" + Number(n).toLocaleString("en-PH", { minimumFractionDigits: 2 }));
export const when = (t) => (t ? new Date(t).toLocaleString() : "-");