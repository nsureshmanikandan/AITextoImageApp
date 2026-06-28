import { useMutation } from '@tanstack/react-query';
import { submitGeneration, regenerateImage } from '@/api/generateApi';
import type { GenerateImageParams, RegenerateParams } from '@/types';

export function useGenerateImage() {
  return useMutation({
    mutationFn: (params: GenerateImageParams) => submitGeneration(params),
  });
}

export function useRegenerateImage() {
  return useMutation({
    mutationFn: (params: RegenerateParams) => regenerateImage(params),
  });
}
