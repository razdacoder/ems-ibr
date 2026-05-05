import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface UploadResult {
  created: number;
  updated: number;
}

function useUploadHook(url: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      const res = await api.post<UploadResult>(url, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries(),
  });
}

export function useUploadDepartments() {
  return useUploadHook("/uploads/departments/");
}

export function useUploadHalls() {
  return useUploadHook("/uploads/halls/");
}

export function useUploadCourses() {
  return useUploadHook("/uploads/courses/");
}

export function useUploadClassesForDepartment(deptSlug: string) {
  return useUploadHook(`/uploads/classes/${deptSlug}/`);
}

export function useUploadClassCourses(classId: number) {
  return useUploadHook(`/uploads/class-courses/${classId}/`);
}

export function useUploadClassStudents(classId: number) {
  return useUploadHook(`/uploads/class-students/${classId}/`);
}

export interface BulkUploadResult extends UploadResult {
  upload_type: string;
}

export function useBulkUpload() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: { file: File; upload_type: string }) => {
      const formData = new FormData();
      formData.append("file", data.file);
      formData.append("upload_type", data.upload_type);
      const res = await api.post<BulkUploadResult>(
        "/uploads/bulk/",
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
        },
      );
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries(),
  });
}
