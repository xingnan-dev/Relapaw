export const PET_IMAGE_ACCEPT = "image/jpeg,image/png,image/webp";
export const PET_IMAGE_MAX_BYTES = 5 * 1024 * 1024;

const supportedPetImageTypes = new Set(PET_IMAGE_ACCEPT.split(","));

export function validatePetImageSelection(file: File): string | null {
  if (!supportedPetImageTypes.has(file.type) || file.size === 0 || file.size > PET_IMAGE_MAX_BYTES) {
    return "照片需为 JPG、PNG 或 WebP，且不超过 5 MB。";
  }
  return null;
}

export function createPetImagePreview(file: File): string {
  return URL.createObjectURL(file);
}

export function releasePetImagePreview(url: string | null): void {
  if (url) URL.revokeObjectURL(url);
}
