export const STAFF_DATA = [
  { id: 1, name: "Luna Smith", role: "Admin", status: "Active", email: "luna.smith@aryanoble.co.id" },
  { id: 2, name: "Sarah Johnson", role: "Manager", status: "Active", email: "sarah.j@aryanoble.co.id" },
  { id: 3, name: "Michael Brown", role: "Staff", status: "Inactive", email: "michael.b@aryanoble.co.id" },
]

export const DOCTOR_DATA = [
  { id: 1, name: "Dr. Aurora Chen", branch: "ERHA Clinic Kemanggisan", speciality: "Dermatologist", tokensLeft: 2450, status: "Active", maxTokens: 5000 },
  { id: 2, name: "Dr. Vivian Lumina", branch: "ERHA Clinic Kelapa Gading", speciality: "Dermatologist", tokensLeft: 1200, status: "Active", maxTokens: 5000 },
  { id: 3, name: "Dr. Jasper Stone", branch: "ERHA Clinic Pondok Indah", speciality: "Aesthetic Doctor", tokensLeft: 500, status: "Warning", maxTokens: 2000 },
  { id: 4, name: "Dr. Iris Thorne", branch: "ERHA Clinic Kemanggisan", speciality: "Dermatologist", tokensLeft: 0, status: "Inactive", maxTokens: 3000 },
]

export type Staff = typeof STAFF_DATA[0]
export type Doctor = typeof DOCTOR_DATA[0]
