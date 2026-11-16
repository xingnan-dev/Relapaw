import { describe, expect, it, vi } from "vitest";
import { createPetImagePreview, PET_IMAGE_MAX_BYTES, releasePetImagePreview, validatePetImageSelection } from "./petImage";

describe("pet image browser boundary", () => {
  it.each(["image/jpeg", "image/png", "image/webp"])("accepts a non-empty supported %s selection", (type) => {
    expect(validatePetImageSelection(new File(["image"], "pet", { type }))).toBeNull();
  });

  it("rejects unsupported, empty and oversized selections before upload", () => {
    expect(validatePetImageSelection(new File(["gif"], "pet.gif", { type: "image/gif" }))).toMatch(/JPG/);
    expect(validatePetImageSelection(new File([], "empty.png", { type: "image/png" }))).toMatch(/JPG/);
    expect(validatePetImageSelection(new File([new Uint8Array(PET_IMAGE_MAX_BYTES + 1)], "large.jpg", { type: "image/jpeg" }))).toMatch(/5 MB/);
  });

  it("owns and releases browser preview URLs", () => {
    const create = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:pet-preview");
    const revoke = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
    const file = new File(["image"], "pet.png", { type: "image/png" });
    expect(createPetImagePreview(file)).toBe("blob:pet-preview");
    releasePetImagePreview("blob:pet-preview");
    expect(create).toHaveBeenCalledWith(file);
    expect(revoke).toHaveBeenCalledWith("blob:pet-preview");
  });
});
