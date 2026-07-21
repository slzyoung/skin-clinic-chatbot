export interface ConfigResponse {
  key: string;
  value: string;
}

export interface ConfigUpdate {
  value: string;
}

export interface BranchBase {
  name: string;
  address?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  image_url?: string | null;
  token_limit: number;
}

export type BranchCreate = BranchBase;

export interface BranchUpdate {
  token_limit: number;
}

export interface BranchDoctorResponse {
  id: string;
  name: string;
  speciality: string;
  tokensLeft: number;
  status: string;
  maxTokens: number;
}

export interface BranchResponse extends BranchBase {
  id: string;
  created_at: string;
  updated_at: string;
  
  tokensMonth: number;
  used: number;
  remaining: number;
  
  doctors: BranchDoctorResponse[];
}
