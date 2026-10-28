import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { PetSetup } from "./PetSetup";

const api = vi.hoisted(() => ({ createPet: vi.fn(), uploadPetAvatar: vi.fn() }));
const setCurrentPet = vi.fn();
vi.mock("../api", () => api);
vi.mock("../state/CurrentPetContext", () => ({ useCurrentPet: () => ({ setCurrentPet }) }));

const pet = { id: 7, name: "豆包", species: "狗", avatar: null };

function completeRequiredFields() {
  fireEvent.change(screen.getByLabelText("名字"), { target: { value: "豆包" } });
  fireEvent.change(screen.getByLabelText("物种"), { target: { value: "狗" } });
  fireEvent.click(screen.getByRole("button", { name: "继续补充一点" }));
}

function chooseAvatar(file: File) {
  fireEvent.change(screen.getByLabelText(/宠物照片/), { target: { files: [file] } });
}

describe("PetSetup recoverable avatar flow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    api.createPet.mockResolvedValue(pet);
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:preview");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
  });

  it("releases the local preview URL when setup is left", () => {
    const view = render(<PetSetup onDone={vi.fn()} onSkip={vi.fn()} />);
    completeRequiredFields();
    chooseAvatar(new File(["jpg"], "pet.jpg", { type: "image/jpeg" }));
    view.unmount();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:preview");
  });

  it("uploads a valid image and completes setup", async () => {
    api.uploadPetAvatar.mockResolvedValue({ id: 3, original_filename: "pet.jpg" });
    const onDone = vi.fn();
    render(<PetSetup onDone={onDone} onSkip={vi.fn()} />);
    completeRequiredFields();
    chooseAvatar(new File([new Uint8Array([0xff, 0xd8, 0xff])], "pet.jpg", { type: "image/jpeg" }));
    fireEvent.click(screen.getByRole("button", { name: "完成建档" }));
    await waitFor(() => expect(onDone).toHaveBeenCalledTimes(1));
    expect(api.createPet).toHaveBeenCalledTimes(1);
    expect(api.uploadPetAvatar).toHaveBeenCalledTimes(1);
  });

  it("keeps the created pet when upload fails and retries without a duplicate", async () => {
    api.uploadPetAvatar.mockRejectedValueOnce(new Error("upload failed")).mockResolvedValueOnce({ id: 3, original_filename: "宠物照片.jpg" });
    const onDone = vi.fn();
    render(<PetSetup onDone={onDone} onSkip={vi.fn()} />);
    completeRequiredFields();
    chooseAvatar(new File([new Uint8Array([0xff, 0xd8, 0xff])], "宠物照片.jpg", { type: "image/jpeg" }));
    fireEvent.click(screen.getByRole("button", { name: "完成建档" }));
    expect(await screen.findByText(/宠物档案已保存，但照片上传失败/)).toBeInTheDocument();
    expect(setCurrentPet).toHaveBeenCalledWith(pet);
    expect(onDone).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "重试上传照片" }));
    await waitFor(() => expect(onDone).toHaveBeenCalledTimes(1));
    expect(api.createPet).toHaveBeenCalledTimes(1);
    expect(api.uploadPetAvatar).toHaveBeenCalledTimes(2);
  });

  it("can enter the app after upload failure without losing the pet", async () => {
    api.uploadPetAvatar.mockRejectedValue(new Error("upload failed"));
    const onDone = vi.fn();
    render(<PetSetup onDone={onDone} onSkip={vi.fn()} />);
    completeRequiredFields();
    chooseAvatar(new File(["jpg"], "pet.jpg", { type: "image/jpeg" }));
    fireEvent.click(screen.getByRole("button", { name: "完成建档" }));
    fireEvent.click(await screen.findByRole("button", { name: "暂时跳过，进入首页" }));
    expect(onDone).toHaveBeenCalledTimes(1);
    expect(api.createPet).toHaveBeenCalledTimes(1);
  });

  it.each([
    ["unsupported", new File(["gif"], "pet.gif", { type: "image/gif" })],
    ["oversized", new File([new Uint8Array(5 * 1024 * 1024 + 1)], "pet.jpg", { type: "image/jpeg" })],
  ])("rejects an %s file before creating the pet", (_label, file) => {
    render(<PetSetup onDone={vi.fn()} onSkip={vi.fn()} />);
    completeRequiredFields();
    chooseAvatar(file);
    expect(screen.getByRole("alert")).toHaveTextContent(/JPG、PNG 或 WebP/);
    expect(api.createPet).not.toHaveBeenCalled();
  });
});
