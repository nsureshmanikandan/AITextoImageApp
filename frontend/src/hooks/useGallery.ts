import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import { fetchGallery } from '@/api/imagesApi';
import { deleteImage } from '@/api/imagesApi';
import type { GalleryFilters } from '@/types';

export function useGallery(filters: GalleryFilters) {
  return useQuery({
    queryKey: ['gallery', filters],
    queryFn: () => fetchGallery(filters),
    staleTime: 30_000,
  });
}

export function useDeleteImage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (imageId: string) => deleteImage(imageId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['gallery'] });
    },
  });
}
