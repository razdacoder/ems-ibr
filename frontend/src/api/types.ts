export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface DepartmentRef {
  id: number;
  name: string;
  slug: string;
}

export interface ClassRef {
  id: number;
  name: string | null;
}
