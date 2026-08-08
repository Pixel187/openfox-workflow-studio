import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import PromptField from "../components/PromptField";

describe("PromptField", () => {
  it("affiche la valeur et propage les changements", () => {
    const onChange = vi.fn();
    render(<PromptField value="Bonjour" onChange={onChange} />);
    const textarea = screen.getByRole("textbox");
    expect(textarea).toHaveValue("Bonjour");
    fireEvent.change(textarea, { target: { value: "Salut" } });
    expect(onChange).toHaveBeenCalledWith("Salut");
  });

  it("insère une variable au drop à la position du curseur", () => {
    const onChange = vi.fn();
    render(<PromptField value="Fais le travail" onChange={onChange} />);
    const textarea = screen.getByRole("textbox");
    // curseur après "Fais le "
    fireEvent.select(textarea, { target: { selectionStart: 8, selectionEnd: 8 } });
    fireEvent.drop(textarea, {
      dataTransfer: { getData: () => "{{workdir}}" },
    });
    expect(onChange).toHaveBeenCalledWith("Fais le {{workdir}}travail");
  });

  it("ignore un drop sans donnée", () => {
    const onChange = vi.fn();
    render(<PromptField value="Fais le travail" onChange={onChange} />);
    const textarea = screen.getByRole("textbox");
    fireEvent.drop(textarea, {
      dataTransfer: { getData: () => "" },
    });
    expect(onChange).not.toHaveBeenCalled();
  });
});