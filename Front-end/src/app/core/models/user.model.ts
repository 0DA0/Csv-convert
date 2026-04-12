// src/app/core/models/user.model.ts — TAMAMEN DEĞİŞTİR

export interface User {
  id: string;
  email: string;
  user_type: 'individual' | 'company' | 'employee';
  data_source: 'csv' | 'clockify';
  profile: IndividualProfile | CompanyProfile | EmployeeProfile;
}

export interface IndividualProfile {
  full_name: string;
  phone?: string;
}

export interface CompanyProfile {
  company_name: string;
  company_code?: string;
  contact_person?: string;
  phone?: string;
  address?: string;
  logo_base64?: string;
}

export interface EmployeeProfile {
  full_name: string;
  phone?: string;
  clockify_username?: string;
  company_id: string;
  company_name: string;
  company_code: string;
  status: 'active' | 'inactive';
}

export interface AuthResponse {
  access_token: string;
  user: User;
}