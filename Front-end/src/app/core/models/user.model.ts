export interface User {
  id: string;
  email: string;
  user_type: 'individual' | 'company';
  data_source: 'csv' | 'clockify';  // YENİ
  profile: IndividualProfile | CompanyProfile;
}

export interface IndividualProfile {
  full_name: string;
  phone?: string;
}

export interface CompanyProfile {
  company_name: string;
  contact_person?: string;
  phone?: string;
  address?: string;
  logo_base64?: string;
}

export interface AuthResponse {
  access_token: string;
  user: User;
}