import { describe, expect, it } from "bun:test";

import cardsNetworkFixture from "../fixtures/cards.network.redacted.json";
import detailNetworkFixture from "../fixtures/detail.network.redacted.json";
import cardsDomHtml from "../fixtures/cards.dom.redacted.html" with { type: "text" };
import {
  EXTRACTOR_VERSION,
  extractCardsFromDomFallback,
  extractCardsFromNetwork,
  extractDetailFromNetwork,
} from "../src/extraction";

describe("liepin worker extraction", () => {
  it("extracts candidate cards from redacted network payloads", () => {
    const cards = extractCardsFromNetwork(cardsNetworkFixture);

    expect(cards).toHaveLength(2);
    expect(cards[0]).toMatchObject({
      provider: "liepin",
      providerCandidateId: "cand-redacted-1",
      extractionSource: "network",
      extractorVersion: EXTRACTOR_VERSION,
      rawPayload: cardsNetworkFixture.data.cards[0],
      privacy: {
        redactionPolicyVersion: "liepin-fixture-redaction-v1",
        containsDirectContact: false,
      },
    });
    expect(cards[0]?.searchableText).toContain("Senior Backend Engineer");
    expect(cards[0]?.searchableText).toContain("Python");
    expect(cards[0]?.missingFields).toEqual([]);
  });

  it("extracts candidate detail from redacted network payloads", () => {
    const detail = extractDetailFromNetwork(detailNetworkFixture);

    expect(detail).toMatchObject({
      provider: "liepin",
      providerCandidateId: "cand-redacted-1",
      providerDetailId: "detail-redacted-1",
      extractionSource: "network",
      extractorVersion: EXTRACTOR_VERSION,
      rawPayload: detailNetworkFixture.data.detail,
      privacy: {
        redactionPolicyVersion: "liepin-fixture-redaction-v1",
        containsDirectContact: false,
      },
    });
    expect(detail.searchableText).toContain("distributed systems");
    expect(detail.searchableText).toContain("Kubernetes");
    expect(detail.missingFields).toEqual([]);
  });

  it("extracts candidate cards from DOM fallback HTML when network payloads are absent", () => {
    const result = extractCardsFromDomFallback(String(cardsDomHtml));

    expect(result.cards).toHaveLength(1);
    expect(result.selectorHealth).toEqual({
      cardSelector: true,
      idSelector: true,
      titleSelector: true,
    });
    expect(result.cards[0]).toMatchObject({
      provider: "liepin",
      providerCandidateId: "dom-cand-redacted-1",
      extractionSource: "dom_fallback",
      extractorVersion: EXTRACTOR_VERSION,
      rawPayload: {
        providerCandidateId: "dom-cand-redacted-1",
        title: "Data Platform Engineer",
        company: "Redacted Analytics",
        skills: ["Python", "Spark"],
      },
      privacy: {
        redactionPolicyVersion: "liepin-fixture-redaction-v1",
        containsDirectContact: false,
      },
    });
    expect(result.cards[0]?.searchableText).toContain("Data Platform Engineer");
  });
});
