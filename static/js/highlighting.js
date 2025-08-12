/**
 * Text highlighting functionality
 * This script allows users to highlight text in the extracted content
 * and automatically highlights examples based on success criteria
 */

// Store highlights for saving
window.savedHighlights = window.savedHighlights || {};
// Variable to track current writing ID - use window object to avoid redeclaration issues
window.currentWritingId = window.currentWritingId || null;

// Function to safely escape HTML special characters
function escapeHtml(text) {
    if (typeof text !== 'string') return '';
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// Function to clean text of HTML and special characters
function cleanText(text) {
    // First remove any HTML tags
    text = text.replace(/<[^>]*>/g, '');
    // Remove any HTML entities
    text = text.replace(/&[^;]+;/g, '');
    // Normalize whitespace
    text = text.replace(/\s+/g, ' ').trim();
    return text;
}

// Function to create a dynamic tooltip
function createTooltip(text, x, y) {
    // Remove any existing tooltips
    const existingTooltips = document.querySelectorAll('.highlight-tooltip');
    existingTooltips.forEach(t => t.remove());
    
    const tooltip = document.createElement('div');
    tooltip.className = 'highlight-tooltip';
    tooltip.textContent = text;
    document.body.appendChild(tooltip);

    // Position the tooltip
    const rect = tooltip.getBoundingClientRect();
    tooltip.style.left = `${Math.min(x, window.innerWidth - rect.width - 10)}px`;
    tooltip.style.top = `${y - rect.height - 10}px`;
    
    // Add manual close button
    const closeButton = document.createElement('span');
    closeButton.textContent = '×';
    closeButton.className = 'tooltip-close';
    closeButton.style.position = 'absolute';
    closeButton.style.right = '5px';
    closeButton.style.top = '2px';
    closeButton.style.cursor = 'pointer';
    closeButton.style.fontSize = '14px';
    closeButton.style.fontWeight = 'bold';
    
    closeButton.addEventListener('click', () => {
        tooltip.remove();
    });
    
    tooltip.appendChild(closeButton);
    tooltip.style.paddingRight = '20px'; // Make room for the close button
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
        tooltip.remove();
    }, 3000);

    return tooltip;
}

// Function to find examples based on criteria type
function findExamplesForCriteria(text, criteriaType) {
    console.log(`Finding examples for criteria: ${criteriaType}`);
    let examples = [];

    // Clean and normalize text
    text = cleanText(text);
    
    // Unified approach to text segmentation - preprocess all text
    const sentences = text.split(/[.!?]+/);
    const allWords = text.split(/\s+/);
    const normalizedText = text.toLowerCase();
    const paragraphs = text.split(/\n+/).filter(p => p.trim().length > 0);
    const firstParagraph = paragraphs.length > 0 ? paragraphs[0] : '';
    const firstSentence = sentences.length > 0 ? sentences[0] : '';
    
    // Base criteria type detection - extract core concept
    const criteriaLower = criteriaType.toLowerCase();
    
    // Assignment-specific criteria detection
    
    // Check for "Use headline" criteria
    if (criteriaLower.includes('headline') || criteriaLower.includes('title')) {
        // Headlines are typically the first sentence or paragraph
        // First, check if there's a clear title pattern
        const titlePattern = /^(.+?)(?::|-)(.+)/;
        const titleMatch = text.match(titlePattern);
        
        if (titleMatch) {
            // There's a colon or dash indicating a headline (e.g., "Breaking News: Children Find Pearl")
            examples.push({
                text: titleMatch[0].trim(),
                context: titleMatch[0].trim(),
                confidence: 0.95
            });
        } else if (firstSentence && firstSentence.trim().length > 0) {
            // No clear title pattern, check if first sentence looks like a headline
            // Headlines usually short, possibly with capitalization, and often ends with punctuation
            const possibleHeadline = firstSentence.trim();
            
            // Check for headline indicators (length, capitalization)
            const isShort = possibleHeadline.split(/\s+/).length <= 15;
            const hasMultipleCapitalized = (possibleHeadline.match(/\b[A-Z][a-z]+/g) || []).length >= 2;
            
            if (isShort) {
                examples.push({
                    text: possibleHeadline,
                    context: possibleHeadline,
                    confidence: hasMultipleCapitalized ? 0.9 : 0.75
                });
            }
            
            // Check if the first line is separated from the rest by a blank line
            if (paragraphs.length >= 2 && paragraphs[0].trim() !== "") {
                examples.push({
                    text: paragraphs[0].trim(),
                    context: paragraphs[0].trim(),
                    confidence: 0.85
                });
            }
        }
        
        // If we couldn't find any headline through patterns, just use the first line as a fallback
        if (examples.length === 0 && text.trim().length > 0) {
            // Try to extract the first line
            const firstLine = text.split("\n")[0].trim();
            if (firstLine.length > 0) {
                examples.push({
                    text: firstLine,
                    context: firstLine,
                    confidence: 0.7 // Lower confidence as this is a fallback
                });
            }
        }
    }
    
    // Check for "Use formal tone" criteria
    else if (criteriaLower.includes('formal tone') || criteriaLower.includes('formality')) {
        // More comprehensive list of formal language indicators
        const formalPhrases = [
            'according to', 'in addition', 'furthermore', 'consequently', 'therefore',
            'subsequently', 'as a result', 'thus', 'hence', 'nevertheless',
            'in conclusion', 'in summary', 'to summarize', 'in regards to',
            'moreover', 'additionally', 'however', 'regarding', 'concerning',
            'in respect to', 'with reference to', 'it is evident that', 'it can be concluded',
            'research indicates', 'significant', 'substantial', 'considerable',
            'demonstrates', 'indicates', 'reveals', 'suggests', 'illustrates',
            'reported', 'stated', 'estimated', 'confirmed', 'highlighted', 'emphasized',
            'extraordinary', 'fascinating', 'remarkable', 'extraordinary'
        ];
        
        // News-specific formal terms
        if (text.toLowerCase().includes('news') || text.toLowerCase().includes('report')) {
            formalPhrases.push(...[
                'discovery', 'according to experts', 'specialists confirm', 
                'investigation reveals', 'officials reported', 'experts say',
                'sources confirm', 'studies show', 'evidence suggests',
                'authorities stated', 'research demonstrates'
            ]);
        }
        
        sentences.forEach(sentence => {
            const lowerSentence = sentence.toLowerCase();
            
            // Check for formal phrases
            for (const phrase of formalPhrases) {
                if (lowerSentence.includes(phrase)) {
                    examples.push({
                        text: sentence.trim(),
                        context: sentence.trim(),
                        confidence: 0.85
                    });
                    break;
                }
            }
            
            // Check for absence of contractions as a formal tone indicator
            if (!lowerSentence.match(/\b(don't|won't|can't|isn't|aren't|hasn't|haven't|didn't|couldn't|wouldn't|shouldn't)\b/i)) {
                // Look for expanded forms
                if (lowerSentence.match(/\b(do not|will not|cannot|is not|are not|has not|have not|did not|could not|would not|should not)\b/i)) {
                    examples.push({
                        text: sentence.trim(),
                        context: sentence.trim(),
                        confidence: 0.8
                    });
                }
            }
            
            // Check for formal sentence structures
            const hasPassiveVoice = lowerSentence.match(/\b(is|are|was|were|be|been|being)\s+\w+ed\b/i);
            if (hasPassiveVoice) {
                examples.push({
                    text: sentence.trim(),
                    context: sentence.trim(),
                    confidence: 0.8
                });
            }
            
            // Check for academic/technical vocabulary (longer words often indicate formality)
            const words = lowerSentence.split(/\s+/);
            const longWords = words.filter(word => word.length > 8);
            if (longWords.length >= 1) {
                examples.push({
                    text: sentence.trim(),
                    context: sentence.trim() + " (contains formal vocabulary: " + longWords.join(", ") + ")",
                    confidence: 0.75
                });
            }
        });
        
        // Check news-specific formal patterns
        if (text.toLowerCase().includes('discovery') || text.toLowerCase().includes('report')) {
            // Look for journalist attribution patterns
            const attributionPattern = /(said|stated|reported|according to|confirmed|revealed|announced|explained|noted)\s+([A-Z][a-z]+)/g;
            let match;
            
            while ((match = attributionPattern.exec(text)) !== null) {
                const attributionPhrase = match[0];
                const startIdx = Math.max(0, match.index - 30);
                const endIdx = Math.min(text.length, match.index + attributionPhrase.length + 30);
                
                // Get expanded context around the attribution
                const context = text.substring(startIdx, endIdx);
                
                examples.push({
                    text: attributionPhrase,
                    context: context,
                    confidence: 0.9
                });
            }
        }
    }
    
    // Check for "Use past tense" criteria
    else if (criteriaLower.includes('past tense') || criteriaLower.includes('simple and progressive')) {
        // Common regular past tense verbs end with -ed
        const pastTenseRegExp = /\b\w+ed\b/g;
        let match;
        
        // Find all past tense verbs
        while ((match = pastTenseRegExp.exec(normalizedText)) !== null) {
            const pastVerb = match[0];
            const verbIndex = allWords.findIndex(word => 
                word.toLowerCase().replace(/[^\w]/g, '') === pastVerb);
            
            if (verbIndex !== -1) {
                // Get context around the verb
                const start = Math.max(0, verbIndex - 3);
                const end = Math.min(allWords.length, verbIndex + 4);
                const context = allWords.slice(start, end).join(' ');
                
                examples.push({
                    text: pastVerb,
                    context: context,
                    confidence: 0.85
                });
            }
        }
        
        // Also check for common irregular past tense verbs
        const irregularPastVerbs = [
            'was', 'were', 'had', 'did', 'said', 'made', 'went', 'took', 'came',
            'saw', 'knew', 'got', 'gave', 'found', 'thought', 'told', 'became',
            'left', 'felt', 'put', 'brought', 'began', 'kept', 'held', 'wrote',
            'stood', 'heard', 'let', 'meant', 'set', 'met', 'ran', 'paid', 'sat',
            'spoke', 'lay', 'led', 'read', 'grew', 'lost', 'fell', 'sent', 'built', 
            'understood', 'drew'
        ];
        
        allWords.forEach((word, index) => {
            const cleanWord = word.toLowerCase().replace(/[^\w]/g, '');
            if (irregularPastVerbs.includes(cleanWord)) {
                // Get context
                const start = Math.max(0, index - 3);
                const end = Math.min(allWords.length, index + 4);
                const context = allWords.slice(start, end).join(' ');
                
                examples.push({
                    text: word,
                    context: context,
                    confidence: 0.9
                });
            }
        });
    }
    
    // Check for "Write in third person" criteria
    else if (criteriaLower.includes('third person')) {
        // Third person pronouns and indicators
        const thirdPersonPronouns = [
            'he', 'she', 'it', 'they', 'him', 'her', 'them', 'his', 'hers', 'its',
            'their', 'theirs', 'himself', 'herself', 'itself', 'themselves'
        ];
        
        // Third person verb forms
        const thirdPersonVerbs = /\b\w+(s|es)\b/g;
        
        // Check for third person pronouns
        allWords.forEach((word, index) => {
            const cleanWord = word.toLowerCase().replace(/[^\w]/g, '');
            if (thirdPersonPronouns.includes(cleanWord)) {
                const start = Math.max(0, index - 2);
                const end = Math.min(allWords.length, index + 3);
                const context = allWords.slice(start, end).join(' ');
                
                examples.push({
                    text: word,
                    context: context,
                    confidence: 0.9
                });
            }
        });
        
        // Check for third person verb forms (verbs ending in s/es)
        let match;
        while ((match = thirdPersonVerbs.exec(normalizedText)) !== null) {
            const verbForm = match[0];
            // Make sure it's not a plural noun by checking context
            const verbIndex = allWords.findIndex(word => 
                word.toLowerCase().replace(/[^\w]/g, '') === verbForm);
            
            if (verbIndex > 0) {
                const prevWord = allWords[verbIndex-1].toLowerCase().replace(/[^\w]/g, '');
                // If previous word is a third person subject, it's likely a verb
                if (thirdPersonPronouns.includes(prevWord) || 
                    ['the', 'a', 'an', 'this', 'that'].includes(prevWord)) {
                    
                    const start = Math.max(0, verbIndex - 3);
                    const end = Math.min(allWords.length, verbIndex + 4);
                    const context = allWords.slice(start, end).join(' ');
                    
                    examples.push({
                        text: allWords[verbIndex],
                        context: context,
                        confidence: 0.8
                    });
                }
            }
        }
    }
    
    // Check for "Direct speech" criteria
    else if (criteriaLower.includes('direct speech') || criteriaLower.includes('speech')) {
        // Look for quotation marks and speech patterns
        const speechMarks = /["']([^"']+)["']/g;
        let match;
        
        while ((match = speechMarks.exec(text)) !== null) {
            const quote = match[0];
            const startIdx = Math.max(0, match.index - 30);
            const endIdx = Math.min(text.length, match.index + quote.length + 30);
            
            // Get expanded context around the quote
            const context = text.substring(startIdx, endIdx);
            
            examples.push({
                text: quote,
                context: context,
                confidence: 0.95 // Very high confidence for quoted text
            });
        }
    }
    
    // Check for paragraph organization criteria
    else if (criteriaLower.includes('paragraph') || criteriaLower.includes('organise') || criteriaLower.includes('organize')) {
        // Look for paragraphs with clear topic sentences
        paragraphs.forEach(paragraph => {
            if (paragraph.trim().length === 0) return;
            
            // Get the first sentence of the paragraph (likely the topic sentence)
            const paragraphSentences = paragraph.split(/[.!?]+/);
            if (paragraphSentences.length > 0) {
                const topicSentence = paragraphSentences[0].trim();
                
                // If it's a substantial sentence, include it
                if (topicSentence.split(/\s+/).length >= 5) {
                    examples.push({
                        text: topicSentence,
                        context: paragraph.substring(0, Math.min(100, paragraph.length)) + '...',
                        confidence: 0.75
                    });
                }
            }
        });
    }
    
    // Check for punctuation criteria
    else if (criteriaLower.includes('punctuation') || criteriaLower.includes('full stop') || 
             criteriaLower.includes('comma') || criteriaLower.includes('capital')) {
        
        // Look for properly punctuated sentences
        sentences.forEach(sentence => {
            const trimmed = sentence.trim();
            if (trimmed.length === 0) return;
            
            // Check for proper capitalization at start
            const startsWithCapital = /^[A-Z]/.test(trimmed);
            
            // Check for commas followed by lowercase letters (not ending)
            const hasCommas = trimmed.includes(',');
            
            if (startsWithCapital && hasCommas) {
                examples.push({
                    text: trimmed,
                    context: trimmed,
                    confidence: 0.8
                });
            }
        });
        
        // Look for fronted adverbials with commas
        const frontedAdverbialPatterns = [
            /^(Eventually|Finally|Fortunately|Unfortunately|Surprisingly|Suddenly|Today|Yesterday|Tomorrow|Meanwhile|Afterwards|Later|Earlier|Soon|Now|Then),/i,
            /^(In fact|In contrast|On the other hand|As a result|For instance|For example|In conclusion|In summary|To conclude|To summarize),/i,
            /^(In the \w+|On the \w+|At the \w+|During the \w+|Before the \w+|After the \w+|Inside the \w+),/i
        ];
        
        sentences.forEach(sentence => {
            const trimmed = sentence.trim();
            if (trimmed.length === 0) return;
            
            for (const pattern of frontedAdverbialPatterns) {
                if (pattern.test(trimmed)) {
                    // Extract the fronted adverbial
                    const match = trimmed.match(pattern);
                    if (match && match[0]) {
                        examples.push({
                            text: match[0],
                            context: trimmed,
                            confidence: 0.9
                        });
                    }
                    break;
                }
            }
        });
    }
    
    // Enhanced pronoun detection
    if (criteriaLower.includes('pronoun')) {
        // Comprehensive pronoun map with categorization
        const pronounMap = {
            personal: {
                subject: ['I', 'you', 'he', 'she', 'it', 'we', 'they'],
                object: ['me', 'you', 'him', 'her', 'it', 'us', 'them']
            },
            possessive: {
                determiners: ['my', 'your', 'his', 'her', 'its', 'our', 'their'],
                pronouns: ['mine', 'yours', 'his', 'hers', 'its', 'ours', 'theirs']
            },
            reflexive: ['myself', 'yourself', 'himself', 'herself', 'itself', 'ourselves', 'yourselves', 'themselves'],
            relative: ['who', 'whom', 'whose', 'which', 'that', 'where', 'when'],
            interrogative: ['who', 'what', 'which', 'where', 'when', 'why', 'how'],
            demonstrative: ['this', 'that', 'these', 'those'],
            indefinite: [
                'all', 'another', 'any', 'anybody', 'anyone', 'anything', 
                'both', 'each', 'either', 'everybody', 'everyone', 'everything',
                'few', 'many', 'most', 'neither', 'nobody', 'none', 'no one',
                'nothing', 'one', 'other', 'others', 'several', 'some',
                'somebody', 'someone', 'something'
            ]
        };
        
        // Flatten the pronoun map for easy lookup
        const allPronouns = new Set();
        Object.values(pronounMap).forEach(category => {
            if (typeof category === 'object' && !Array.isArray(category)) {
                Object.values(category).forEach(subcategory => {
                    subcategory.forEach(pronoun => allPronouns.add(pronoun.toLowerCase()));
                });
            } else if (Array.isArray(category)) {
                category.forEach(pronoun => allPronouns.add(pronoun.toLowerCase()));
            }
        });
        
        // Check for specific pronoun types if mentioned in criteria
        let targetPronouns = allPronouns;
        if (criteriaLower.includes('personal')) {
            targetPronouns = new Set([
                ...pronounMap.personal.subject.map(p => p.toLowerCase()),
                ...pronounMap.personal.object.map(p => p.toLowerCase())
            ]);
        } else if (criteriaLower.includes('possessive')) {
            targetPronouns = new Set([
                ...pronounMap.possessive.determiners.map(p => p.toLowerCase()),
                ...pronounMap.possessive.pronouns.map(p => p.toLowerCase())
            ]);
        } else if (criteriaLower.includes('reflexive')) {
            targetPronouns = new Set(pronounMap.reflexive.map(p => p.toLowerCase()));
        } else if (criteriaLower.includes('relative')) {
            targetPronouns = new Set(pronounMap.relative.map(p => p.toLowerCase()));
        } else if (criteriaLower.includes('demonstrative')) {
            targetPronouns = new Set(pronounMap.demonstrative.map(p => p.toLowerCase()));
        } else if (criteriaLower.includes('indefinite')) {
            targetPronouns = new Set(pronounMap.indefinite.map(p => p.toLowerCase()));
        }
        
        // Enhanced detection
        allWords.forEach((word, index) => {
            const cleanWord = word.replace(/[^\w]/g, '').toLowerCase();
            if (targetPronouns.has(cleanWord)) {
                // Get expanded context for better understanding
                const start = Math.max(0, index - 3);
                const end = Math.min(allWords.length, index + 4);
                const context = allWords.slice(start, end).join(' ');
                
                examples.push({
                    text: word, // Use original form with punctuation for better highlighting
                    context: context,
                    confidence: 0.9 // High confidence for direct matches
                });
            }
        });
    } 
    
    // Enhanced complex sentence detection
    else if (criteriaLower.includes('complex sentence')) {
        // Expanded subordinating conjunctions for improved detection
        const complexMarkers = [
            // Time relationships
            'after', 'before', 'when', 'while', 'until', 'since', 'as soon as', 'whenever', 'once',
            // Cause and effect
            'because', 'since', 'as', 'so that', 'in order that', 'now that',
            // Contrast or unexpected results
            'although', 'though', 'even though', 'whereas', 'while', 'unless',
            // Conditions
            'if', 'unless', 'only if', 'provided that', 'assuming that', 'even if',
            // Other relationships
            'wherever', 'however', 'rather than', 'than', 'whether', 'in case'
        ];

        sentences.forEach(sentence => {
            if (sentence.trim() === '') return;
            const lowerSentence = sentence.toLowerCase();
            
            // Multi-clause detection - more nuanced approach
            let isComplex = false;
            
            // Check for subordinating conjunctions
            for (const marker of complexMarkers) {
                // Use word boundary for more precise matching
                const pattern = new RegExp(`\\b${escapeRegExp(marker)}\\b`, 'i');
                if (pattern.test(lowerSentence)) {
                    isComplex = true;
                    break;
                }
            }
            
            // Check for comma + clause structure that often indicates complex sentences
            if (!isComplex && sentence.includes(',')) {
                const clauses = sentence.split(',');
                if (clauses.length >= 2) {
                    // More sophisticated subject-verb check
                    const hasSubjectVerb = (text) => {
                        const words = text.trim().split(/\s+/);
                        // Need at least 2 words for subject-verb
                        if (words.length < 2) return false;
                        
                        // Simple heuristic: check for pronoun/noun followed by word not in prepositions list
                        const prepositions = new Set(['in', 'on', 'at', 'by', 'for', 'with', 'from', 'to']);
                        for (let i = 0; i < words.length - 1; i++) {
                            if (!prepositions.has(words[i].toLowerCase()) && 
                                !prepositions.has(words[i+1].toLowerCase())) {
                                return true;
                            }
                        }
                        return false;
                    };
                    
                    // Check both clauses for subject-verb structure
                    if (hasSubjectVerb(clauses[0]) && hasSubjectVerb(clauses[1])) {
                        isComplex = true;
                    }
                }
            }
            
            // Relative clause indicators
            const relativePronouns = ['who', 'whom', 'whose', 'which', 'that'];
            for (const pronoun of relativePronouns) {
                const pattern = new RegExp(`\\b${pronoun}\\b`, 'i');
                if (pattern.test(lowerSentence)) {
                    isComplex = true;
                    break;
                }
            }
            
            if (isComplex) {
                examples.push({
                    text: sentence.trim(),
                    context: sentence.trim(),
                    confidence: 0.85 // Good confidence for complex sentence detection
                });
            }
        });
    } 
    
    // Enhanced coordinating conjunction detection
    else if (criteriaLower.includes('coordinating conjunction')) {
        // FANBOYS - For, And, Nor, But, Or, Yet, So
        const conjunctions = ['for', 'and', 'nor', 'but', 'or', 'yet', 'so'];
        
        sentences.forEach(sentence => {
            if (sentence.trim() === '') return;
            const lowerSentence = sentence.toLowerCase();
            
            // Look for coordinating conjunction patterns
            conjunctions.forEach(conj => {
                // More precise detection with word boundaries
                const pattern = new RegExp(`\\b${conj}\\b`, 'i');
                
                if (pattern.test(lowerSentence)) {
                    let confidence = 0.5; // Base confidence
                    
                    // Compound sentence indicator: comma + conjunction
                    const commaConjPattern = new RegExp(`,\\s*\\b${conj}\\b`, 'i');
                    if (commaConjPattern.test(lowerSentence)) {
                        confidence = 0.9; // High confidence for comma + conjunction pattern
                    } 
                    // List pattern: X, Y, and Z
                    else if (/,.*,.*\b(and|or)\b/.test(lowerSentence)) {
                        confidence = 0.8; // Good confidence for list pattern
                    }
                    // Less common conjunctions are more likely to be true coordinating uses
                    else if (conj !== 'and' && conj !== 'or') {
                        confidence = 0.7; // Medium-high confidence
                    }
                    
                    // Only include high-quality examples
                    if (confidence > 0.5) {
                        examples.push({
                            text: sentence.trim(),
                            context: sentence.trim(),
                            confidence: confidence
                        });
                    }
                }
            });
        });
    } 
    
    // Enhanced adjective detection
    else if (criteriaLower.includes('adjective')) {
        // Expanded adjective list with categorization
        const adjectiveCategories = {
            descriptive: [
                'big', 'small', 'large', 'tiny', 'huge', 'tall', 'short', 'long', 'wide', 'narrow',
                'heavy', 'light', 'thick', 'thin', 'deep', 'shallow', 'high', 'low'
            ],
            color: [
                'red', 'blue', 'green', 'yellow', 'black', 'white', 'orange', 'purple', 
                'pink', 'brown', 'gray', 'grey', 'silver', 'golden', 'dark', 'bright'
            ],
            feelings: [
                'happy', 'sad', 'angry', 'excited', 'worried', 'anxious', 'calm', 'peaceful',
                'joyful', 'miserable', 'afraid', 'brave', 'confident', 'nervous', 'proud'
            ],
            quality: [
                'good', 'bad', 'excellent', 'terrible', 'wonderful', 'awful', 'perfect', 'poor',
                'beautiful', 'ugly', 'gorgeous', 'handsome', 'pretty', 'lovely', 'pleasant', 'horrible'
            ],
            age: [
                'new', 'old', 'young', 'ancient', 'modern', 'fresh', 'recent', 'antique'
            ]
        };
        
        // Flatten adjective categories for lookup
        const commonAdjectives = new Set();
        Object.values(adjectiveCategories).forEach(category => {
            category.forEach(adj => commonAdjectives.add(adj));
        });
        
        // Adjective suffixes - expanded list
        const adjectiveSuffixes = [
            'able', 'ible', 'al', 'ial', 'an', 'ian', 'ant', 'ary', 'ate', 'ative',
            'ent', 'etic', 'ful', 'ic', 'ical', 'ient', 'ile', 'ine', 'ish', 'ive',
            'less', 'like', 'ly', 'ory', 'ous', 'some', 'y'
        ];

        // Smart adjective detection with pattern recognition
        sentences.forEach(sentence => {
            if (sentence.trim() === '') return;
            
            const words = sentence.split(/\s+/);
            for (let i = 0; i < words.length; i++) {
                const word = words[i].replace(/[^\w]/g, '').toLowerCase();
                if (word.length <= 2) continue; // Skip very short words
                
                let isAdjective = false;
                let confidence = 0;
                
                // Method 1: Known adjective
                if (commonAdjectives.has(word)) {
                    isAdjective = true;
                    confidence = 0.9; // High confidence for known adjectives
                }
                
                // Method 2: Suffix matching
                if (!isAdjective) {
                    for (const suffix of adjectiveSuffixes) {
                        if (word.endsWith(suffix) && word.length > suffix.length + 1) {
                            isAdjective = true;
                            confidence = 0.7; // Medium confidence for suffix matching
                            break;
                        }
                    }
                }
                
                // Method 3: Position-based detection (before nouns)
                if (!isAdjective && i < words.length - 1) {
                    // Check for determiner + potential adjective + noun pattern
                    const determiners = ['the', 'a', 'an', 'this', 'that', 'these', 'those', 'my', 'your', 'his', 'her'];
                    const prevWord = i > 0 ? words[i-1].replace(/[^\w]/g, '').toLowerCase() : '';
                    const nextWord = words[i+1].replace(/[^\w]/g, '').toLowerCase();
                    
                    // If preceded by determiner and not a common verb, likely an adjective
                    if (determiners.includes(prevWord) && 
                        !['is', 'are', 'was', 'were', 'be', 'been', 'being'].includes(word)) {
                        isAdjective = true;
                        confidence = 0.6; // Lower confidence for position-based detection
                    }
                }
                
                if (isAdjective) {
                    // Get expanded context for better understanding
                    const start = Math.max(0, i - 2);
                    const end = Math.min(words.length, i + 3);
                    const context = words.slice(start, end).join(' ');
                    
                    examples.push({
                        text: word,
                        context: context,
                        confidence: confidence
                    });
                }
            }
        });
    } 
    
    // Enhanced adverb detection
    else if (criteriaLower.includes('adverb')) {
        // Adverb category definitions for enhanced detection
        const adverbCategories = {
            manner: [
                'quickly', 'slowly', 'carefully', 'carelessly', 'happily', 'sadly', 'eagerly',
                'reluctantly', 'loudly', 'quietly', 'beautifully', 'poorly', 'well', 'badly'
            ],
            time: [
                'now', 'then', 'today', 'tomorrow', 'yesterday', 'soon', 'later', 'earlier',
                'immediately', 'suddenly', 'eventually', 'recently', 'currently', 'finally'
            ],
            frequency: [
                'always', 'usually', 'often', 'frequently', 'sometimes', 'occasionally', 
                'rarely', 'seldom', 'never', 'daily', 'weekly', 'monthly', 'yearly'
            ],
            degree: [
                'very', 'extremely', 'quite', 'rather', 'somewhat', 'almost', 'nearly',
                'completely', 'entirely', 'absolutely', 'totally', 'barely', 'hardly'
            ],
            place: [
                'here', 'there', 'everywhere', 'nowhere', 'anywhere', 'somewhere',
                'upstairs', 'downstairs', 'inside', 'outside', 'abroad', 'overhead'
            ]
        };
        
        // Common adverbs that don't end in -ly
        const irregularAdverbs = new Set([
            'very', 'too', 'quite', 'rather', 'almost', 'always', 'never', 'well',
            'fast', 'hard', 'late', 'long', 'soon', 'still', 'today', 'tomorrow',
            'yesterday', 'now', 'then', 'often', 'seldom', 'here', 'there', 'just'
        ]);
        
        // Position patterns for adverbs
        const positionPatterns = [
            // Before verbs
            /\b(\w+ly)\s+(\w+ed|s|\w+ing)\b/i,
            // After auxiliary verbs
            /\b(is|are|was|were|have|has|had)\s+(\w+ly)\b/i,
            // At sentence start with comma
            /^(\w+ly),/i
        ];
        
        sentences.forEach(sentence => {
            if (sentence.trim() === '') return;
            const lowerSentence = sentence.toLowerCase();
            
            // Method 1: -ly suffix detection
            const words = sentence.split(/\s+/);
            words.forEach((word, index) => {
                const cleanWord = word.replace(/[^\w]/g, '').toLowerCase();
                if (cleanWord.length <= 2) return; // Skip very short words
                
                let isAdverb = false;
                let confidence = 0;
                
                // Check for -ly ending (most common adverb indicator)
                if (cleanWord.endsWith('ly') && cleanWord.length > 3) {
                    isAdverb = true;
                    confidence = 0.8; // High confidence for -ly words
                }
                // Check for irregular adverbs
                else if (irregularAdverbs.has(cleanWord)) {
                    isAdverb = true;
                    confidence = 0.9; // Very high confidence for known irregular adverbs
                }
                
                // Position-based detection
                if (!isAdverb && index > 0 && index < words.length - 1) {
                    // Check typical adverb positions
                    const prevWord = words[index-1].replace(/[^\w]/g, '').toLowerCase();
                    const nextWord = words[index+1].replace(/[^\w]/g, '').toLowerCase();
                    
                    // After auxiliary verbs
                    if (['is', 'are', 'was', 'were', 'have', 'has', 'had'].includes(prevWord)) {
                        isAdverb = true;
                        confidence = 0.6;
                    }
                    // Before main verbs
                    else if (nextWord.endsWith('ed') || nextWord.endsWith('ing') || nextWord.endsWith('s')) {
                        isAdverb = true;
                        confidence = 0.5;
                    }
                }
                
                if (isAdverb) {
                    const start = Math.max(0, index - 2);
                    const end = Math.min(words.length, index + 3);
                    const context = words.slice(start, end).join(' ');
                    
                    examples.push({
                        text: cleanWord,
                        context: context,
                        confidence: confidence
                    });
                }
            });
            
            // Method 2: Pattern-based detection for sentence-level adverbs
            for (const pattern of positionPatterns) {
                const matches = lowerSentence.match(pattern);
                if (matches && matches.length > 1) {
                    examples.push({
                        text: matches[1],
                        context: sentence.trim(),
                        confidence: 0.7
                    });
                }
            }
        });
    } 
    
    // Enhanced relative clause detection
    else if (criteriaLower.includes('relative clause')) {
        const relativePronouns = ['who', 'whom', 'whose', 'which', 'that', 'where', 'when'];
        
        sentences.forEach(sentence => {
            if (sentence.trim() === '') return;
            const lowerSentence = sentence.toLowerCase();
            
            for (const pronoun of relativePronouns) {
                // More precise detection with context analysis
                const pattern = new RegExp(`\\b${pronoun}\\b`, 'i');
                
                if (pattern.test(lowerSentence)) {
                    // Check if likely a true relative clause
                    // Relative clauses typically follow a noun and contain a verb
                    let confidence = 0.7; // Default confidence
                    
                    // Boost confidence for specific patterns
                    if (pronoun !== 'that') {
                        // 'that' can be ambiguous - other relative pronouns are clearer
                        confidence = 0.85;
                    }
                    
                    // Check for commas - often indicate non-restrictive relative clauses
                    if (lowerSentence.includes(`, ${pronoun} `)) {
                        confidence = 0.9; // Very high confidence
                    }
                    
                    examples.push({
                        text: sentence.trim(),
                        context: sentence.trim(),
                        confidence: confidence
                    });
                    
                    // Only find the first instance per sentence to avoid duplicates
                    break;
                }
            }
        });
    } 
    
    // Enhanced modal verb detection
    else if (criteriaLower.includes('modal verb')) {
        // Comprehensive modal verb list with categorization
        const modalMap = {
            possibility: ['can', 'could', 'may', 'might'],
            necessity: ['must', 'have to', 'has to', 'had to', 'need to', 'needs to', 'needed to'],
            prediction: ['will', 'would', 'shall', 'should'],
            advisability: ['should', 'ought to', 'had better', 'would rather']
        };
        
        // Flatten modal categories for lookup
        const allModals = [];
        Object.values(modalMap).forEach(category => {
            category.forEach(modal => allModals.push(modal));
        });
        
        // Find instances of modal verbs with context
        sentences.forEach(sentence => {
            if (sentence.trim() === '') return;
            const lowerSentence = sentence.toLowerCase();
            
            for (const modal of allModals) {
                // Handle multi-word modals
                if (modal.includes(' ')) {
                    if (lowerSentence.includes(modal)) {
                        examples.push({
                            text: modal,
                            context: sentence.trim(),
                            confidence: 0.9
                        });
                    }
                } else {
                    // For single-word modals, use word boundary check
                    const pattern = new RegExp(`\\b${modal}\\b`, 'i');
                    if (pattern.test(lowerSentence)) {
                        // Get specific context around the modal
                        const modalIndex = lowerSentence.indexOf(modal);
                        const start = Math.max(0, modalIndex - 15);
                        const end = Math.min(sentence.length, modalIndex + modal.length + 15);
                        const context = sentence.substring(start, end).trim();
                        
                        examples.push({
                            text: modal,
                            context: context,
                            confidence: 0.9
                        });
                    }
                }
            }
        });
    } 
    
    // Enhanced preposition detection
    else if (criteriaLower.includes('preposition')) {
        // Expanded preposition list with categorization
        const prepositionCategories = {
            location: [
                'in', 'on', 'at', 'inside', 'outside', 'above', 'below', 'under', 'underneath',
                'beneath', 'beside', 'behind', 'in front of', 'near', 'next to', 'between',
                'among', 'opposite'
            ],
            direction: [
                'to', 'toward', 'towards', 'from', 'into', 'onto', 'out of', 'up', 'down', 
                'along', 'around', 'through', 'across', 'over', 'under', 'past'
            ],
            time: [
                'at', 'in', 'on', 'for', 'during', 'before', 'after', 'since', 'until', 
                'till', 'by', 'within', 'throughout'
            ],
            other: [
                'of', 'with', 'without', 'by', 'for', 'about', 'against', 'despite', 
                'except', 'like', 'unlike', 'as', 'beyond', 'regarding', 'concerning'
            ]
        };
        
        // Flatten preposition categories for lookup
        const allPrepositions = [];
        Object.values(prepositionCategories).forEach(category => {
            category.forEach(prep => allPrepositions.push(prep));
        });
        
        // Process text for prepositions
        allWords.forEach((word, index) => {
            const cleanWord = word.replace(/[^\w]/g, '').toLowerCase();
            
            // Check single-word prepositions
            if (allPrepositions.includes(cleanWord)) {
                const start = Math.max(0, index - 3);
                const end = Math.min(allWords.length, index + 4);
                const context = allWords.slice(start, end).join(' ');
                
                examples.push({
                    text: cleanWord,
                    context: context,
                    confidence: 0.9
                });
            }
            
            // Check multi-word prepositions
            const multiWordPreps = allPrepositions.filter(prep => prep.includes(' '));
            if (index < allWords.length - 1) {
                for (const prep of multiWordPreps) {
                    const prepWords = prep.split(' ');
                    if (cleanWord === prepWords[0]) {
                        // Check if subsequent words match the multi-word preposition
                        let isMatch = true;
                        for (let i = 1; i < prepWords.length; i++) {
                            if (index + i >= allWords.length || 
                                allWords[index + i].replace(/[^\w]/g, '').toLowerCase() !== prepWords[i]) {
                                isMatch = false;
                                break;
                            }
                        }
                        
                        if (isMatch) {
                            const start = Math.max(0, index - 2);
                            const end = Math.min(allWords.length, index + prepWords.length + 2);
                            const context = allWords.slice(start, end).join(' ');
                            
                            examples.push({
                                text: prep,
                                context: context,
                                confidence: 0.9
                            });
                        }
                    }
                }
            }
        });
    } 
    
    // Enhanced verb detection (excluding modal verbs)
    else if (criteriaLower.includes('verb') && !criteriaLower.includes('modal')) {
        // Skip common auxiliary verbs
        const auxiliaryVerbs = new Set([
            'am', 'is', 'are', 'was', 'were', 'be', 'being', 'been', 
            'have', 'has', 'had', 'do', 'does', 'did', 'get', 'got', 'gotten'
        ]);

        // Common strong verbs that might not have typical verb endings
        const strongVerbs = new Set([
            'run', 'jump', 'swim', 'climb', 'fly', 'fight', 'throw', 'catch',
            'build', 'create', 'destroy', 'break', 'shatter', 'crush', 'discover',
            'believe', 'think', 'know', 'want', 'need', 'like', 'love', 'hate', 
            'hope', 'feel', 'see', 'hear', 'make', 'take', 'give', 'find', 'put',
            'read', 'write', 'speak', 'talk', 'shout', 'whisper', 'ask', 'answer',
            'eat', 'drink', 'sleep', 'wake', 'dream', 'laugh', 'cry', 'smile'
        ]);
        
        // Process text for verbs
        sentences.forEach(sentence => {
            if (sentence.trim() === '') return;
            
            const words = sentence.split(/\s+/);
            words.forEach((word, index) => {
                const cleanWord = word.replace(/[^\w]/g, '').toLowerCase();
                if (cleanWord.length <= 2) return; // Skip very short words
                
                let isVerb = false;
                let confidence = 0;
                
                // Method 1: Known strong verbs
                if (strongVerbs.has(cleanWord)) {
                    isVerb = true;
                    confidence = 0.9;
                }
                
                // Method 2: Common verb endings
                if (!isVerb) {
                    if (/ed$/.test(cleanWord) && cleanWord.length > 3) {
                        isVerb = true;
                        confidence = 0.85; // Past tense
                    } else if (/ing$/.test(cleanWord) && cleanWord.length > 4) {
                        isVerb = true;
                        confidence = 0.85; // Present participle
                    } else if (/s$/.test(cleanWord) && !/ss$|us$|is$|as$|os$/.test(cleanWord) && cleanWord.length > 3) {
                        isVerb = true;
                        confidence = 0.7; // Potential present tense (could be plural noun)
                    } else if (/es$/.test(cleanWord) && cleanWord.length > 4) {
                        isVerb = true;
                        confidence = 0.7; // Potential present tense
                    }
                }
                
                // Method 3: Position-based detection
                if (!isVerb && index > 0) {
                    const prevWord = words[index-1].replace(/[^\w]/g, '').toLowerCase();
                    
                    // After subject pronouns, likely a verb
                    if (['i', 'you', 'he', 'she', 'we', 'they'].includes(prevWord)) {
                        isVerb = true;
                        confidence = 0.6;
                    }
                    // After auxiliaries, likely a main verb
                    else if (['will', 'would', 'shall', 'should', 'can', 'could', 'may', 'might', 'must'].includes(prevWord)) {
                        isVerb = true;
                        confidence = 0.8;
                    }
                    // After 'to', likely an infinitive verb
                    else if (prevWord === 'to' && !/ing$/.test(cleanWord)) {
                        isVerb = true;
                        confidence = 0.8;
                    }
                }
                
                // Skip auxiliary verbs
                if (isVerb && !auxiliaryVerbs.has(cleanWord)) {
                    // Get context
                    const start = Math.max(0, index - 2);
                    const end = Math.min(words.length, index + 3);
                    const context = words.slice(start, end).join(' ');

                    examples.push({
                        text: cleanWord,
                        context: context
                    });
                }
            });
        });
    } else if (criteriaType.toLowerCase().includes('compound sentence')) {
        // Look for compound sentences (two independent clauses joined by a coordinating conjunction)
        const coordinatingConjunctions = ['and', 'but', 'or', 'nor', 'for', 'yet', 'so'];
        const sentences = text.split(/[.!?]+/);

        sentences.forEach(sentence => {
            if (sentence.trim() === '') return;

            // Look for the pattern: [clause], [coordinating conjunction] [clause]
            coordinatingConjunctions.forEach(conj => {
                const pattern = new RegExp(`,\\s*\\b${conj}\\b\\s+`, 'i');
                if (pattern.test(sentence)) {
                    examples.push({
                        text: sentence.trim(),
                        context: sentence.trim()
                    });
                }
            });
        });
    } else if (criteriaType.toLowerCase().includes('vocabulary') || 
               criteriaType.toLowerCase().includes('descriptive language') ||
               criteriaType.toLowerCase().includes('expression')) {
        // Look for less common words that might indicate sophisticated vocabulary
        const commonWords = new Set([
            'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i', 
            'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
            'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
            'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what',
            'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me',
            'when', 'make', 'can', 'like', 'time', 'no', 'just', 'him', 'know', 'take',
            'people', 'into', 'year', 'your', 'good', 'some', 'could', 'them', 'see', 'other',
            'than', 'then', 'now', 'look', 'only', 'come', 'its', 'over', 'think', 'also'
        ]);

        const sentences = text.split(/[.!?]+/);
        sentences.forEach(sentence => {
            if (sentence.trim() === '') return;

            const words = sentence.split(/\s+/);
            let uncommonWordCount = 0;
            let uncommonWords = [];

            for (let i = 0; i < words.length; i++) {
                const word = words[i].replace(/[^\w]/g, '').toLowerCase();
                // Skip short words and common words
                if (word.length > 5 && !commonWords.has(word)) {
                    uncommonWordCount++;
                    uncommonWords.push(word);
                }
            }

            // If the sentence has enough uncommon words, consider it an example
            if (uncommonWordCount >= 2 || (words.length > 10 && uncommonWordCount >= 1)) {
                examples.push({
                    text: sentence.trim(),
                    context: sentence.trim(),
                    keywords: uncommonWords
                });
            }
        });
    }

    // Remove duplicates (based on context)
    const uniqueExamples = [];
    const seenContexts = new Set();

    examples.forEach(example => {
        if (!seenContexts.has(example.context)) {
            seenContexts.add(example.context);
            uniqueExamples.push(example);
        }
    });

    console.log(`Found ${uniqueExamples.length} unique examples for criteria: ${criteriaType}`);
    return uniqueExamples;
}

/**
 * Extract examples from justification text
 * Enhanced function that identifies various patterns in teacher feedback
 * This is the primary source of criteria examples in the highlighting system
 */
function extractExamplesFromJustification(justification) {
    if (!justification) return [];
    
    console.log("Extracting examples from justification:", justification.substring(0, 100) + "...");
    
    const examplesWithMetadata = [];
    
    // 1. Look for text in single or double quotes - HIGHEST PRIORITY
    const singleQuoteMatches = justification.match(/'([^']+)'/g) || [];
    const doubleQuoteMatches = justification.match(/"([^"]+)"/g) || [];
    
    // Process quoted examples with high priority and confidence
    [...singleQuoteMatches, ...doubleQuoteMatches].forEach(match => {
        const example = match.slice(1, -1).trim();
        if (example.length > 1) {
            console.log("Found quoted example:", example);
            examplesWithMetadata.push({
                text: example,
                confidence: 0.95, // Very high confidence for quoted examples
                priority: 1,      // Highest priority 
                source: 'quoted'
            });
        }
    });
    
    // 2. Look for "Examples include: X, Y, Z" or "such as X, Y, Z" patterns
    const examplesPatterns = [
        /examples include:?\s*([^.]+)/i,
        /such as:?\s*([^.]+)/i,
        /for example:?\s*([^.]+)/i,
        /e\.g\.:?\s*([^.]+)/i,
        /including:?\s*([^.]+)/i,
        /like:?\s*([^.]+)/i
    ];
    
    examplesPatterns.forEach(pattern => {
        const match = justification.match(pattern);
        if (match && match[1]) {
            // Split by commas and clean up
            const items = match[1].split(/,\s*|\sand\s+/)
                .map(item => item.trim().replace(/["']/g, ''))
                .filter(item => item.length > 1);
            
            // Add each example with priority 2
            items.forEach(item => {
                examplesWithMetadata.push({
                    text: item,
                    confidence: 0.9,
                    priority: 2,  // Second highest priority
                    source: 'listed'
                });
            });
        }
    });
    
    // 3. Look for action verbs that indicate examples
    const actionVerbPatterns = [
        /used\s+["']?([^"'.;,]+)["']?/i,
        /wrote\s+["']?([^"'.;,]+)["']?/i,
        /included\s+["']?([^"'.;,]+)["']?/i,
        /added\s+["']?([^"'.;,]+)["']?/i,
        /applied\s+["']?([^"'.;,]+)["']?/i,
        /demonstrated\s+["']?([^"'.;,]+)["']?/i,
        /incorporated\s+["']?([^"'.;,]+)["']?/i
    ];
    
    actionVerbPatterns.forEach(pattern => {
        const match = justification.match(pattern);
        if (match && match[1] && match[1].trim().length > 1) {
            examplesWithMetadata.push({
                text: match[1].trim(),
                confidence: 0.85,
                priority: 3,  // Third priority
                source: 'verb-indicated'
            });
        }
    });
    
    // 4. Look for "The word/phrase X is used" pattern
    const wordPhrasePattern = /the (word|phrase|term|expression)\s+["']?([^"'.]+)["']?/i;
    const wordPhraseMatch = justification.match(wordPhrasePattern);
    
    if (wordPhraseMatch && wordPhraseMatch[2] && wordPhraseMatch[2].trim().length > 1) {
        examplesWithMetadata.push({
            text: wordPhraseMatch[2].trim(),
            confidence: 0.9,
            priority: 2,  // Higher priority for explicit mentions
            source: 'term-indicated'
        });
    }
    
    // 5. Look for text in brackets or parentheses (often used for examples)
    const bracketPattern = /\(([^)]+)\)/g;
    let bracketMatch;
    
    while ((bracketMatch = bracketPattern.exec(justification)) !== null) {
        if (bracketMatch[1].trim().length > 1) {
            examplesWithMetadata.push({
                text: bracketMatch[1].trim(),
                confidence: 0.8,
                priority: 3,
                source: 'bracketed'
            });
        }
    }
    
    // 6. Look for text after colons that could be examples
    const colonPattern = /:\s*["']?([^"'.]+)["']?/g;
    let colonMatch;
    
    while ((colonMatch = colonPattern.exec(justification)) !== null) {
        // If it's not already part of a pattern we matched above
        if (colonMatch[1].trim().length > 1 && 
            !colonMatch[0].match(/examples include:|such as:|for example:|e\.g\.:|including:/i)) {
            examplesWithMetadata.push({
                text: colonMatch[1].trim(),
                confidence: 0.75,
                priority: 4,  // Lower priority
                source: 'colon-indicated'
            });
        }
    }
    
    // Return examples with metadata (already deduplicated by text)
    const uniqueExamples = [];
    const seenTexts = new Set();
    
    // Sort by priority first (lower number = higher priority)
    examplesWithMetadata.sort((a, b) => a.priority - b.priority);
    
    // Then deduplicate, keeping the highest priority instances
    for (const example of examplesWithMetadata) {
        if (!seenTexts.has(example.text)) {
            uniqueExamples.push(example);
            seenTexts.add(example.text);
        }
    }
    
    return uniqueExamples;
}

/**
 * Apply background color to criteria boxes based on score
 * This should be called after the highlightText function has run
 */
function applyCriteriaBoxStyles() {
    console.log("Applying styles to criteria boxes based on scores");
    
    // Find all criteria boxes in the document
    const criteriaBoxes = document.querySelectorAll('.criteria-box');
    
    criteriaBoxes.forEach(box => {
        // Get the score from the box (either from data attribute or looking for score text)
        let score = box.getAttribute('data-score');
        
        if (!score) {
            // Try to find score from the text content, looking for patterns like "Score: X/Y"
            const scoreText = box.textContent.match(/Score:\s*(\d+)\/\d+/i);
            if (scoreText && scoreText[1]) {
                score = parseInt(scoreText[1]);
            }
        }
        
        if (score !== null && score !== undefined) {
            score = parseInt(score, 10); // Ensure score is an integer
            console.log(`Applying style for criteria box with score ${score}`);
            
            // Apply inline background color and border to ensure it takes effect
            if (score === 0) {
                box.style.backgroundColor = '#ffb6c1'; // Light red - pastel
                box.style.borderLeft = '4px solid #f88'; // Darker red border
            } else if (score === 1) {
                box.style.backgroundColor = '#ffffaa'; // Light yellow - pastel
                box.style.borderLeft = '4px solid #cc0'; // Darker yellow border
            } else if (score === 2) {
                box.style.backgroundColor = '#c2f0c2'; // Light green - pastel
                box.style.borderLeft = '4px solid #6c6'; // Darker green border
            }
            
            // Find justification text to extract examples
            const justification = box.querySelector('.text-muted')?.textContent || '';
            const criteria = box.querySelector('strong')?.textContent || '';
            
            if (justification) {
                console.log(`Finding examples in justification for "${criteria}"`);
                
                // Extract examples from the justification
                const examples = extractExamplesFromJustification(justification);
                
                if (examples && examples.length > 0) {
                    console.log(`Found ${examples.length} examples to highlight for criteria "${criteria}"`);
                    
                    // Get all text containers where we might find these examples
                    const textContainers = document.querySelectorAll('.extracted-text, .sample-text');
                    
                    // Apply highlights to each container
                    textContainers.forEach(container => {
                        const originalHtml = container.innerHTML;
                        let newHtml = originalHtml;
                        
                        // Apply each example as a highlight
                        examples.forEach(example => {
                            if (example.text && example.text.length > 3) { // Only process meaningful examples
                                const safeText = escapeRegExp(example.text);
                                const regex = new RegExp(`(${safeText})`, 'gi');
                                newHtml = newHtml.replace(regex, `<span class="criteria-mark-${score}" title="${criteria}" data-tooltip="${criteria} (Score: ${score}/2)">${example.text}</span>`);
                            }
                        });
                        
                        if (newHtml !== originalHtml) {
                            container.innerHTML = newHtml;
                        }
                    });
                } else {
                    console.log(`No examples found for criteria "${criteria}"`);
                }
            }
        }
    });
}

/**
 * Main highlight function - implements the two-pass algorithm
 * @param {string} text - The original text to highlight
 * @param {Array} criteriaMarks - Array of criteria with score, justification, etc.
 * @returns {string} HTML string with highlights applied
 */
function highlightText(text, criteriaMarks) {
    if (!text || !criteriaMarks || !Array.isArray(criteriaMarks)) {
        return text;
    }
    
    // Apply styles to criteria boxes after a short delay to ensure DOM is updated
    setTimeout(applyCriteriaBoxStyles, 200);

    console.log("Starting highlighting with criteria:", criteriaMarks.map(cm => `${cm.criteria || cm.text}: ${cm.score}`).join(', '));
    
    // Show the total count of criteria available for highlighting
    const textElements = document.querySelectorAll('.sample-text');
    if (textElements.length > 0) {
        showCriteriaBadge(textElements[0], criteriaMarks.length);
    }

    // PASS 1: Collect all examples with their scores and criteria info
    const allExamples = [];

    // Comprehensive grammar dictionaries organized by curriculum levels
    const grammarDictionaries = {
        // Pronouns - categorized by type and curriculum level
        'pronouns': {
            'personal': {
                'subject': ['I', 'you', 'he', 'she', 'it', 'we', 'they'],  // Years 1-2
                'object': ['me', 'you', 'him', 'her', 'it', 'us', 'them']  // Years 1-3
            },
            'possessive': {
                'determiners': ['my', 'your', 'his', 'her', 'its', 'our', 'their'],  // Years 1-3
                'pronouns': ['mine', 'yours', 'his', 'hers', 'its', 'ours', 'theirs']  // Years 2-4
            },
            'reflexive': [
                'myself', 'yourself', 'himself', 'herself', 'itself',  // Years 3-4
                'ourselves', 'yourselves', 'themselves'  // Years 3-4
            ],
            'relative': {
                'basic': ['who', 'which', 'that'],  // Years 3-4
                'advanced': ['whom', 'whose', 'where', 'when']  // Years 5-6
            },
            'interrogative': ['who', 'what', 'which', 'where', 'when', 'why', 'how', 'whom', 'whose'],  // Years 1-6
            'demonstrative': ['this', 'that', 'these', 'those'],  // Years 1-3
            'indefinite': [
                'all', 'another', 'any', 'anybody', 'anyone', 'anything',  // Years 3-4
                'both', 'each', 'either', 'everybody', 'everyone', 'everything',  // Years 3-4
                'few', 'many', 'most', 'neither', 'nobody', 'none', 'no one',  // Years 4-5
                'nothing', 'one', 'other', 'others', 'several', 'some',  // Years 4-5
                'somebody', 'someone', 'something', 'such', 'whatever', 'whichever'  // Years 5-6
            ]
        },

        // Conjunctions - by type and complexity
        'coordinating conjunctions': [
            'and', 'but', 'or',  // Years 1-2 (basic)
            'nor', 'for', 'yet', 'so'  // Years 3-4 (advanced)
        ],

        'subordinating conjunctions': {
            'time': [
                'after', 'before', 'when', 'while', 'until', 'since',  // Years 3-4
                'as soon as', 'whenever', 'once', 'by the time'  // Years 5-6
            ],
            'place': ['where', 'wherever'],  // Years 4-5
            'cause/reason': [
                'because', 'as', 'since',  // Years 3-4
                'now that', 'inasmuch as', 'forasmuch as'  // Years 5-6
            ],
            'purpose': [
                'so that', 'in order that', 'in order to',  // Years 4-5
                'lest', 'so as to'  // Years 5-6
            ],
            'condition': [
                'if', 'unless', 'provided that',  // Years 4-5
                'assuming that', 'in case', 'supposing', 'even if'  // Years 5-6
            ],
            'contrast': [
                'although', 'though', 'even though',  // Years 4-5
                'whereas', 'while', 'however'  // Years 5-6
            ],
            'comparison': ['than', 'as', 'as if', 'as though'],  // Years 5-6
            'concession': ['although', 'though', 'even though', 'while']  // Years 5-6
        },

        'correlative conjunctions': [
            'both...and', 'either...or', 'neither...nor',  // Years 4-5
            'not only...but also', 'whether...or'  // Years 5-6
        ],

        // Verbs - by tense, form, and level
        'verbs': {
            'irregular': [
                // Common irregular verbs (Years 1-6)
                'be', 'am', 'is', 'are', 'was', 'were', 'been', 'being',
                'have', 'has', 'had', 'having',
                'do', 'does', 'did', 'done', 'doing',
                'go', 'goes', 'went', 'gone', 'going',
                'see', 'sees', 'saw', 'seen', 'seeing',
                'come', 'comes', 'came', 'coming',
                'get', 'gets', 'got', 'gotten', 'getting',
                'make', 'makes', 'made', 'making',
                'say', 'says', 'said', 'saying',
                'know', 'knows', 'knew', 'known', 'knowing',
                'take', 'takes', 'took', 'taken', 'taking',
                'give', 'gives', 'gave', 'given', 'giving',
                'find', 'finds', 'found', 'finding',
                'think', 'thinks', 'thought', 'thinking',
                'tell', 'tells', 'told', 'telling',
                'write', 'writes', 'wrote', 'written', 'writing',
                'read', 'reads', 'read', 'reading'
            ],
            'action_verbs': [
                // Basic action verbs (Years 1-3)
                'walk', 'run', 'jump', 'play', 'look', 'talk', 'eat', 'drink',
                'sit', 'stand', 'sleep', 'laugh', 'cry', 'smile', 'dance', 'sing',

                // More sophisticated action verbs (Years 4-6)
                'sprint', 'dash', 'leap', 'gallop', 'stroll', 'crawl', 'glide', 'soar',
                'plunge', 'dive', 'charge', 'devour', 'consume', 'whisper', 'mutter',
                'shout', 'bellow', 'screech', 'whimper', 'wail', 'sob', 'chuckle'
            ],
            'linking_verbs': [
                'am', 'is', 'are', 'was', 'were', 'be', 'being', 'been',  // Years 1-3
                'appear', 'become', 'feel', 'grow', 'look', 'remain',  // Years 3-5
                'seem', 'smell', 'sound', 'stay', 'taste', 'turn'  // Years 4-6
            ],
            'helping_verbs': [
                'am', 'is', 'are', 'was', 'were',  // Years 1-3 (be verbs)
                'have', 'has', 'had',  // Years 2-4 (have verbs)
                'do', 'does', 'did',  // Years 2-4 (do verbs)
                'can', 'could', 'may', 'might', 'must',  // Years 3-5 (modal verbs)
                'shall', 'should', 'will', 'would'  // Years 4-6 (modal verbs)
            ],
            'phrasal_verbs': [
                // Years 4-6
                'look up', 'pick up', 'put down', 'turn on', 'turn off',
                'give away', 'take off', 'break down', 'come across', 'find out',
                'grow up', 'look after', 'look forward to', 'put up with', 'run into'
            ]
        },

        // Modal verbs - by function and level
        'modal verbs': {
            'ability': ['can', 'could'],  // Years 2-3
            'permission': ['can', 'could', 'may', 'might'],  // Years 3-4
            'obligation': ['must', 'have to', 'should', 'ought to'],  // Years 4-5
            'prohibition': ['must not', 'cannot', 'should not'],  // Years 4-5
            'possibility': ['may', 'might', 'could'],  // Years 4-5
            'certainty': ['will', 'shall', 'must'],  // Years 4-5
            'prediction': ['will', 'would', 'shall'],  // Years 5-6
            'suggestion': ['should', 'could', 'might', 'shall']  // Years 5-6
        },

        // Adverbs - by type and level
        'adverbs': {
            'manner': [
                // Basic (Years 2-3)
                'quickly', 'slowly', 'loudly', 'quietly', 'well', 'badly', 'fast', 'hard',

                // Advanced (Years 4-6)
                'carefully', 'carelessly', 'anxiously', 'cheerfully', 'eagerly', 'efficiently',
                'fortunately', 'frantically', 'gracefully', 'hastily', 'hungrily', 'mysteriously',
                'obediently', 'patiently', 'perfectly', 'politely', 'promptly', 'reluctantly',
                'rudely', 'silently', 'solemnly', 'suddenly', 'suspiciously', 'swiftly'
            ],
            'time': [
                // Basic (Years 2-3)
                'now', 'then', 'today', 'tomorrow', 'yesterday', 'soon', 'later',

                // Advanced (Years 4-6)
                'afterwards', 'already', 'eventually', 'finally', 'immediately', 'initially',
                'previously', 'recently', 'shortly', 'simultaneously', 'subsequently', 'suddenly'
            ],
            'place': [
                // Basic (Years 2-3)
                'here', 'there', 'nearby', 'far', 'away', 'inside', 'outside',

                // Advanced (Years 4-6)
                'above', 'abroad', 'ahead', 'everywhere', 'nowhere', 'somewhere',
                'backward', 'downward', 'upward', 'eastward', 'northward', 'underneath'
            ],
            'frequency': [
                // Basic (Years 2-3)
                'always', 'never', 'sometimes', 'often', 'rarely',

                // Advanced (Years 4-6)
                'frequently', 'occasionally', 'seldom', 'usually', 'generally', 'hardly',
                'daily', 'weekly', 'monthly', 'yearly', 'constantly', 'continually'
            ],
            'degree': [
                // Basic (Years 2-3)
                'very', 'too', 'quite', 'almost', 'just',

                // Advanced (Years 4-6)
                'absolutely', 'completely', 'entirely', 'extremely', 'greatly', 'highly',
                'nearly', 'perfectly', 'practically', 'rather', 'really', 'terribly', 'utterly'
            ]
        },

        // Prepositions - by type and level
        'prepositions': {
            'place': [
                // Basic (Years 1-2)
                'in', 'on', 'under', 'above', 'below', 'between', 'behind', 'in front of',

                // Intermediate (Years 3-4)
                'among', 'alongside', 'beneath', 'beside', 'beyond', 'inside', 'outside',

                // Advanced (Years 5-6)
                'throughout', 'within', 'without', 'amid', 'amidst', 'across from'
            ],
            'time': [
                // Basic (Years 1-2)
                'at', 'in', 'on', 'after', 'before', 'during',

                // Intermediate (Years 3-4)
                'since', 'until', 'by', 'within', 'throughout',

                // Advanced (Years 5-6)
                'prior to', 'following', 'subsequent to', 'pending'
            ],
            'movement': [
                // Basic (Years 1-3)
                'to', 'from', 'up', 'down', 'across', 'through',

                // Intermediate (Years 3-4)
                'into', 'onto', 'out of', 'off', 'over', 'under',

                // Advanced (Years 5-6)
                'toward', 'towards', 'along', 'around', 'past', 'via'
            ],
            'other': [
                // Basic (Years 1-3)
                'with', 'without', 'by', 'for', 'of', 'about',

                // Intermediate (Years 3-5)
                'against', 'instead of', 'except', 'despite', 'besides',

                // Advanced (Years 5-6)
                'according to', 'because of', 'due to', 'in spite of', 'on behalf of',
                'regarding', 'with respect to', 'concerning', 'notwithstanding'
            ]
        },

        // Adjectives - by type and curriculum level
        'adjectives': {
            'descriptive': {
                // Basic (Years 1-2)
                'basic': [
                    'big', 'small', 'little', 'long', 'short', 'tall', 'high', 'low',
                    'hot', 'cold', 'warm', 'cool', 'old', 'new', 'young', 'good', 'bad',
                    'happy', 'sad', 'angry', 'funny', 'silly', 'nice', 'mean', 'loud', 'quiet'
                ],
                // Intermediate (Years 3-4)
                'intermediate': [
                    'beautiful', 'handsome', 'pretty', 'ugly', 'clean', 'dirty', 'messy',
                    'dangerous', 'safe', 'brave', 'afraid', 'scared', 'friendly', 'kind',
                    'clever', 'smart', 'bright', 'dark', 'light', 'heavy', 'empty', 'full'
                ],
                // Advanced (Years 5-6)
                'advanced': [
                    'magnificent', 'spectacular', 'extraordinary', 'tremendous', 'marvelous',
                    'exquisite', 'picturesque', 'immaculate', 'pristine', 'colossal', 'minuscule',
                    'courageous', 'valiant', 'malevolent', 'benevolent', 'ingenious', 'diligent',
                    'meticulous', 'arduous', 'tedious', 'ambiguous', 'precarious', 'treacherous'
                ]
            },
            'comparative': [
                // Basic (Years 2-3)
                'bigger', 'smaller', 'taller', 'shorter', 'longer', 'higher', 'lower',
                'hotter', 'colder', 'older', 'newer', 'better', 'worse', 'happier', 'sadder',

                // Advanced (Years 4-6)
                'more beautiful', 'more dangerous', 'more interesting', 'more exciting',
                'more difficult', 'more expensive', 'more important', 'more significant'
            ],
            'superlative': [
                // Basic (Years 2-3)
                'biggest', 'smallest', 'tallest', 'shortest', 'longest', 'highest', 'lowest',
                'hottest', 'coldest', 'oldest', 'newest', 'best', 'worst', 'happiest', 'saddest',

                // Advanced (Years 4-6)
                'most beautiful', 'most dangerous', 'most interesting', 'most exciting',
                'most difficult','most expensive', 'most important', 'most significant'
            ]
        },

        // Determiners that introduce nouns - bytype and level
        'determiners': {
            'articles': ['a', 'an', 'the'],  // Years 1-2
            'possessive': ['my', 'your', 'his', 'her', 'its', 'our', 'their'],  // Years 1-3
            'demonstrative': ['this', 'that', 'these', 'those'],  // Years 1-3
            'quantifiers': [
                // Basic (Years 1-3)
                'some', 'any', 'many', 'much', 'few', 'little', 'all', 'both', 'no',

                // Advanced (Years 4-6)
                'several', 'enough', 'each', 'every', 'either', 'neither', 'fewer', 'less',
                'more', 'most', 'plenty of', 'a lot of', 'lots of', 'a few', 'a little'
            ]
        },

        // Sentence structures - by complexity level
        'sentence structures': {
            'simple': 'One independent clause with no dependent clauses',  // Years 1-2
            'compound': 'Two or more independent clauses joined by a coordinating conjunction or semicolon',  // Years 3-4
            'complex': 'One independent clause and at least one dependent clause',  // Years 4-5
            'compound-complex': 'Two or more independent clauses and at least one dependent clause'  // Years 5-6
        },

        // Punctuation - by complexity and curriculum level
        'punctuation': {
            'basic': ['.', '?', '!', ','],  // Years 1-2
            'intermediate': [':', ';', '"', "'", '(', ')'],  // Years 3-4
            'advanced': ['-', '...', '—', '[', ']', '{', '}']  // Years 5-6
        }
    };

    // Flatten dictionaries for easier searching
    const flattenedDictionaries = {};

    for (const category in grammarDictionaries) {
        flattenedDictionaries[category] = [];

        // Check if the category contains subcategories
        if (typeof grammarDictionaries[category] === 'object' && !Array.isArray(grammarDictionaries[category])) {
            for (const subcategory in grammarDictionaries[category]) {
                // Handle nested structures (up to 3 levels deep)
                if (typeof grammarDictionaries[category][subcategory] === 'object' && !Array.isArray(grammarDictionaries[category][subcategory])) {
                    for (const subsubcategory in grammarDictionaries[category][subcategory]) {
                        if (Array.isArray(grammarDictionaries[category][subcategory][subsubcategory])) {
                            flattenedDictionaries[category] = flattenedDictionaries[category].concat(
                                grammarDictionaries[category][subcategory][subsubcategory]
                            );
                        }
                    }
                } else if (Array.isArray(grammarDictionaries[category][subcategory])) {
                    flattenedDictionaries[category] = flattenedDictionaries[category].concat(
                        grammarDictionaries[category][subcategory]
                    );
                }
            }
        } else if (Array.isArray(grammarDictionaries[category])) {
            flattenedDictionaries[category] = grammarDictionaries[category];
        }
    }

    criteriaMarks.forEach(mark => {
        const criteriaName = mark.text || mark.criteria || "Success Criteria";
        const score = mark.score !== undefined ? mark.score : 1; // Default to 1 if missing
        const criteriaLower = criteriaName.toLowerCase();
        const criteriaJustification = mark.justification || '';
        
        console.log(`Processing criteria: "${criteriaName}" with score: ${score}`);
        console.log(`Justification: "${criteriaJustification}"`);

        // First try to get explicit examples from the justification
        const justificationExamples = extractExamplesFromJustification(criteriaJustification);
        
        if (justificationExamples.length > 0) {
            console.log(`Found ${justificationExamples.length} explicit examples in justification`);
            
            // Use the explicit examples provided in justification
            justificationExamples.forEach(example => {
                if (example && example.trim().length >= 1) { // Allow single character examples if explicitly quoted
                    allExamples.push({
                        text: example.trim(),
                        score: score,
                        criteria: criteriaName,
                        exactMatch: true, // Flag for exact matching only
                        priority: 10 // Give highest priority to explicit examples from justification
                    });
                }
            });
        }
        
        // Also look for text sections in the justification that match the text directly
        // This handles when the teacher mentioned examples without quotes
        if (criteriaJustification) {
            const justificationSentences = criteriaJustification.split(/[.;:!?]+/).map(s => s.trim()).filter(s => s.length > 5);
            
            // Look through each sentence for potential examples
            justificationSentences.forEach(sentence => {
                // Skip sentences that are too generic
                if (sentence.toLowerCase().includes('example') || 
                    sentence.toLowerCase().includes('uses') ||
                    sentence.toLowerCase().includes('demonstrates') ||
                    sentence.toLowerCase().includes('criteria')) {
                    return;
                }
                
                // Try to find multi-word phrases (3+ words) in the text
                const words = sentence.split(/\s+/);
                if (words.length >= 3) {
                    // Check for phrases of 3-6 words
                    for (let windowSize = Math.min(6, words.length); windowSize >= 3; windowSize--) {
                        for (let i = 0; i <= words.length - windowSize; i++) {
                            const phrase = words.slice(i, i + windowSize).join(' ');
                            if (phrase.length > 5 && text.includes(phrase)) {
                                console.log(`Found matching phrase in text: "${phrase}"`);
                                allExamples.push({
                                    text: phrase,
                                    score: score,
                                    criteria: criteriaName,
                                    exactMatch: true,
                                    priority: 8
                                });
                                // Break after finding a match in this window to avoid too many overlapping examples
                                break;
                            }
                        }
                    }
                }
            });
        }
        
        // If no examples found from justification, only then fall back to dictionaries or auto-detection
        if (allExamples.filter(ex => ex.criteria === criteriaName).length === 0) {
            console.log(`No examples found in justification for "${criteriaName}", trying fallback methods`);
            
            // Only use minimal dictionary support for specific grammar criteria 
            // (we don't want to overwhelm with generic highlights)
            let dictionaryMatches = [];
            
            if (criteriaLower.includes('headline') || criteriaLower.includes('title')) {
                // Simple headline detection - grab the first line if teacher is looking for a headline
                const firstLine = text.split('\n')[0].trim();
                if (firstLine.length > 3) {
                    dictionaryMatches.push({
                        text: firstLine,
                        score: score,
                        criteria: criteriaName,
                        exactMatch: true,
                        priority: 5
                    });
                }
            } else if (criteriaLower.includes('direct speech') || criteriaLower.includes('speech mark') || criteriaLower.includes('quotation')) {
                // For speech-related criteria, find text in quotes
                const quotesPattern = /["']([^"']+)["']/g;
                let match;
                while ((match = quotesPattern.exec(text)) !== null) {
                    dictionaryMatches.push({
                        text: match[0],
                        score: score,
                        criteria: criteriaName,
                        exactMatch: true,
                        priority: 7
                    });
                    
                    // Limit to top 3 quotes to avoid overwhelming
                    if (dictionaryMatches.length >= 3) break;
                }
            }
            
            if (dictionaryMatches.length > 0) {
                console.log(`Found ${dictionaryMatches.length} matches for "${criteriaName}" using basic detection`);
                allExamples.push(...dictionaryMatches);
            } else {
                // Last resort: only for specific, common criteria types, try auto-detection
                // This is highly restricted to avoid inappropriate automatic highlighting
                let useAutoDetection = false;
                
                // Very limited whitelist of criteria that we might auto-detect
                // RESTRICTED VERSION: Only allow spelling, capitalization and punctuation criteria
                // to be auto-detected, per user request
                const autoDetectableCriteria = [
                    'spelling', 'capital', 'punctuation'
                ];
                
                // Only use auto-detection for whitelisted criteria
                for (const allowedCriteria of autoDetectableCriteria) {
                    if (criteriaLower.includes(allowedCriteria)) {
                        useAutoDetection = true;
                        break;
                    }
                }
                
                if (useAutoDetection) {
                    console.log(`Attempting auto-detection for "${criteriaName}"`);
                    const autoExamples = findExamplesForCriteria(text, criteriaName);
                    
                    // Further limit auto-generated examples to just 2 per criteria
                    autoExamples.slice(0, 2).forEach(example => {
                        allExamples.push({
                            text: example.text,
                            score: score,
                            criteria: criteriaName,
                            exactMatch: false, // Allow partial matching for auto-detected examples
                            priority: 3 // Lowest priority
                        });
                    });
                } else {
                    console.log(`No examples found for "${criteriaName}" and criteria not eligible for auto-detection`);
                }
            }
        }
    });

    // If no examples found, return the original text
    if (allExamples.length === 0) {
        return text;
    }

    // Sort examples by priority (highest first), then by length (longest first)
    allExamples.sort((a, b) => {
        // First sort by priority (if exists)
        if (a.priority !== undefined && b.priority !== undefined) {
            if (a.priority !== b.priority) {
                return b.priority - a.priority; // Higher priority first
            }
        }
        
        // If same priority or priority not set, sort by length
        return b.text.length - a.text.length;
    });

    // PASS 2: Find all occurrences in the text and track their positions
    const matches = [];
    const lowerText = text.toLowerCase();

    allExamples.forEach(example => {
        const searchText = example.text;
        if (!searchText || searchText.trim().length === 0) return;

        const lowerSearchText = searchText.toLowerCase();

        // For single words, we always enforce word boundaries
        const isSingleWord = !searchText.includes(' ');

        // For multi-word phrases, we need to check if they are complete phrases
        const isPhrase = searchText.includes(' ');

        // Different approach based on whether it's a single word or phrase
        if (isSingleWord) {
            // Use regex with word boundaries for single words
            const wordRegex = new RegExp(`\\b${escapeRegExp(lowerSearchText)}\\b`, 'gi');
            let match;

            while ((match = wordRegex.exec(lowerText)) !== null) {
                matches.push({
                    start: match.index,
                    end: match.index + searchText.length,
                    score: example.score,
                    criteria: example.criteria,
                    text: text.substring(match.index, match.index + searchText.length) // Original casing
                });
            }
        } else if (isPhrase) {
            // For phrases, we need to be more careful
            let startIndex = 0;

            while (startIndex < lowerText.length) {
                const foundIndex = lowerText.indexOf(lowerSearchText, startIndex);
                if (foundIndex === -1) break;

                // For phrases, check that the boundaries are correct
                // Ensure the phrase starts at a word boundary or the beginning of text
                const phraseStartValid = foundIndex === 0 || !isAlphaNumeric(lowerText[foundIndex - 1]);

                // Ensure the phrase ends at a word boundary or the end of text
                const phraseEndIndex = foundIndex + lowerSearchText.length;
                const phraseEndValid = phraseEndIndex === lowerText.length || !isAlphaNumeric(lowerText[phraseEndIndex]);

                if (phraseStartValid && phraseEndValid) {
                    matches.push({
                        start: foundIndex,
                        end: foundIndex + searchText.length,
                        score: example.score,
                        criteria: example.criteria,
                        text: text.substring(foundIndex, foundIndex + searchText.length) // Original casing
                    });
                }

                startIndex = foundIndex + 1; // Move past this occurrence
            }
        } else if (!example.exactMatch) {
            // For auto-detected examples, use the previous logic but with stricter word boundary checks
            let startIndex = 0;

            while (startIndex < lowerText.length) {
                const foundIndex = lowerText.indexOf(lowerSearchText, startIndex);
                if (foundIndex === -1) break;

                // Check if this is a whole word/phrase match
                const isWholeWord = (
                    (foundIndex === 0 || !isAlphaNumeric(lowerText[foundIndex - 1])) &&
                    (foundIndex + lowerSearchText.length === lowerText.length || 
                     !isAlphaNumeric(lowerText[foundIndex + lowerSearchText.length]))
                );

                if (isWholeWord) {
                    matches.push({
                        start: foundIndex,
                        end: foundIndex + searchText.length,
                        score: example.score,
                        criteria: example.criteria,
                        text: text.substring(foundIndex, foundIndex + searchText.length) // Original casing
                    });
                }

                startIndex = foundIndex + 1; // Move past this occurrence
            }
        }
    });

    // Sort matches by start position
    matches.sort((a, b) => a.start - b.start);

    // Merge overlapping matches
    const mergedMatches = [];

    if (matches.length > 0) {
        let current = matches[0];

        for (let i = 1; i < matches.length; i++) {
            const next = matches[i];

            if (next.start <= current.end) {
                // Overlapping matches - extend the current one
                current.end = Math.max(current.end, next.end);

                // Keep the higher score and its criteria if scores differ
                if (next.score > current.score) {
                    current.score = next.score;
                    current.criteria = next.criteria;
                }
            } else {
                // No overlap - add current to results and move to next
                mergedMatches.push(current);
                current = next;
            }
        }

        // Don't forget the last match
        mergedMatches.push(current);
    }

    // Build the final highlighted HTML
    let result = '';
    let lastIndex = 0;

    mergedMatches.forEach(match => {
        // Add text before this highlight
        result += escapeHtml(text.substring(lastIndex, match.start));

        // Add the highlighted text
        const highlightedText = escapeHtml(text.substring(match.start, match.end));
        
        // Map scores to CSS classes that indicate achievement level
        let highlightClass;
        if (match.score === 0) highlightClass = 'criteria-mark-0'; // Not meeting criteria
        else if (match.score === 1) highlightClass = 'criteria-mark-1'; // Partially meeting criteria 
        else if (match.score === 2) highlightClass = 'criteria-mark-2'; // Fully meeting criteria
        else highlightClass = 'criteria-mark-1'; // Default to partially meeting if score is undefined
        
        console.log("Highlighting text:", highlightedText, "with class:", highlightClass);
        
        // Add ability to remove highlight with a click (optional) and show criteria in tooltip
        // Include data-criteria attribute to allow CSS to target specific types of criteria
        result += `<span class="${highlightClass}" data-tooltip="${match.criteria}" data-criteria="${match.criteria.toLowerCase()}" data-score="${match.score}">${highlightedText}</span>`;

        lastIndex = match.end;
    });

    // Add any remaining text
    if (lastIndex < text.length) {
        result += escapeHtml(text.substring(lastIndex));
    }

    return result;
}

/**
 * Helper function to escape regex special characters
 */
function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * Helper function to check if a character is alphanumeric
 */
function isAlphaNumeric(char) {
    return /[a-z0-9]/i.test(char);
}

/**
 * Shows a badge with the number of teacher criteria available for highlighting
 * @param {HTMLElement} textElement - The text element container
 * @param {number} criteriaCount - The number of criteria available
 */
function showCriteriaBadge(textElement, criteriaCount) {
    if (!textElement || criteriaCount <= 0) return;
    
    // Find the badge container near the text element
    const container = textElement.closest('.text-content');
    if (!container) return;
    
    // Check if there's already a criteria badge
    let badge = container.querySelector('.criteria-badge');
    if (!badge) {
        badge = document.createElement('span');
        badge.className = 'badge bg-success criteria-badge';
        badge.style.position = 'relative';
        badge.style.top = '-5px';
        badge.style.marginLeft = '8px';
        
        const toggleButton = container.querySelector('.toggle-highlight-mode');
        if (toggleButton && toggleButton.parentNode) {
            toggleButton.parentNode.insertBefore(badge, toggleButton.nextSibling);
        }
    }
    
    badge.innerHTML = `<i class="fa fa-check-circle me-1"></i> ${criteriaCount} Criteria`;
}

/**
 * Create and manage custom tooltips to ensure they're fully visible
 */
function setupTooltipPositioning() {
    console.log("Setting up global tooltip system");
    
    // Create a single tooltip element that will be reused
    let tooltip = document.getElementById('global-tooltip');
    if (!tooltip) {
        tooltip = document.createElement('div');
        tooltip.id = 'global-tooltip';
        tooltip.className = 'custom-tooltip';
        tooltip.style.display = 'none';
        tooltip.style.position = 'fixed';
        tooltip.style.zIndex = '10000';
        document.body.appendChild(tooltip);
    }

    // Track the current target element
    let currentTarget = null;
    
    // Add global mouseover event for all elements with data-tooltip
    document.addEventListener('mouseover', function(e) {
        const target = e.target.closest('[data-tooltip]');
        if (target) {
            const tooltipText = target.getAttribute('data-tooltip');
            if (tooltipText) {
                // Show tooltip
                tooltip.textContent = tooltipText;
                tooltip.style.display = 'block';
                
                // Position tooltip relative to target
                positionTooltip(tooltip, target);
                
                // Remember current target
                currentTarget = target;
            }
        }
    });
    
    // Hide tooltip when mouse leaves relevant elements
    document.addEventListener('mouseout', function(e) {
        if (currentTarget && !currentTarget.contains(e.relatedTarget) && !tooltip.contains(e.relatedTarget)) {
            tooltip.style.display = 'none';
            currentTarget = null;
        }
    });
    
    // Update tooltip position on scroll
    document.addEventListener('scroll', function() {
        if (currentTarget && tooltip.style.display !== 'none') {
            positionTooltip(tooltip, currentTarget);
        }
    }, { passive: true });
    
    function positionTooltip(tooltip, target) {
        const rect = target.getBoundingClientRect();
        
        // Calculate position above the element
        let top = rect.top - tooltip.offsetHeight - 10;
        let left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2);
        
        // If not enough space above, position below
        if (top < 5) {
            top = rect.bottom + 10;
        }
        
        // Adjust horizontal position to fit on screen
        if (left < 5) {
            left = 5;
        } else if (left + tooltip.offsetWidth > window.innerWidth - 5) {
            left = window.innerWidth - tooltip.offsetWidth - 5;
        }
        
        // Apply position
        tooltip.style.top = top + 'px';
        tooltip.style.left = left + 'px';
    }
}

/**
 * Apply AI highlights to a text element based on criteria marks
 * Enhanced version with automated criteria detection and confidence scoring
 */
async function applyAIHighlights(textElement) {
    if (!textElement) {
        console.log("No text element provided");
        return;
    }

    if (!textElement.innerHTML) {
        console.log("No content or text to highlight");
        return;
    }

    console.log('Applying AI highlights to text element:', textElement);

    // Use the content text rather than innerHTML to avoid any existing HTML
    const contentText = textElement.textContent;
    
    // Try to find criteria marks in the DOM
    const criteriaItems = [];
    
    // First look for assignment criteria list items (teacher-defined success criteria)
    const assignmentCriteriaRows = document.querySelectorAll('.criteria-list-item, .criteria-row, .success-criteria-item');
    if (assignmentCriteriaRows.length > 0) {
        console.log(`Found ${assignmentCriteriaRows.length} assignment criteria items`);
        assignmentCriteriaRows.forEach(row => criteriaItems.push(row));
    }
    
    // If no assignment criteria found, try generic list items (fallback)
    if (criteriaItems.length === 0) {
        const listItems = document.querySelectorAll('.list-group-item');
        listItems.forEach(row => criteriaItems.push(row));
        console.log(`Found ${listItems.length} generic list items as fallback`);
    }
    
    // Also check for criteria in the feedback section
    const feedbackSection = document.querySelector('.feedback-section, .analysis-feedback');
    if (feedbackSection) {
        const strengthsSection = feedbackSection.querySelector('.strengths-section, .strengths');
        const developmentSection = feedbackSection.querySelector('.development-section, .areas-for-development');
        
        if (strengthsSection) {
            // Extract criteria from strengths bullets
            const strengthItems = strengthsSection.querySelectorAll('li, p');
            strengthItems.forEach(item => {
                // Extract criteria from the strength description
                const text = item.textContent.trim();
                if (text.includes(':')) {
                    const criteriaText = text.split(':')[0].trim();
                    criteriaItems.push({
                        isCustomFeedback: true,
                        criteriaText: criteriaText,
                        justification: text,
                        score: 2 // Strengths are fully met
                    });
                }
            });
        }
        
        if (developmentSection) {
            // Extract criteria from development areas bullets
            const developmentItems = developmentSection.querySelectorAll('li, p');
            developmentItems.forEach(item => {
                // Extract criteria from the development description
                const text = item.textContent.trim();
                if (text.includes(':')) {
                    const criteriaText = text.split(':')[0].trim();
                    criteriaItems.push({
                        isCustomFeedback: true,
                        criteriaText: criteriaText,
                        justification: text,
                        score: 1 // Areas for development are partially met
                    });
                }
            });
        }
    }

    // Extract criteria marks with enhanced metadata
    const criteriaMarks = [];
    criteriaItems.forEach(item => {
        // Check if this is a custom feedback item we processed above
        if (item.isCustomFeedback) {
            criteriaMarks.push({
                text: item.criteriaText,
                criteria: item.criteriaText,
                score: item.score,
                justification: item.justification
            });
            return;
        }
        
        let criteriaText = '';
        let score = -1;
        let justification = '';

        // Try to parse from criteria elements
        const badgeElement = item.querySelector('.badge, .criteria-score, .score-badge');
        if (badgeElement) {
            criteriaText = item.textContent.replace(badgeElement.textContent, '').trim();

            const scoreBadge = badgeElement.textContent.trim();
            if (scoreBadge.includes('0')) score = 0;
            else if (scoreBadge.includes('1')) score = 1;
            else if (scoreBadge.includes('2')) score = 2;

            // Try to find justification in a data attribute or child element
            justification = item.dataset.justification || '';
            if (!justification) {
                const justificationEl = item.querySelector('.criteria-justification, .justification, .mb-0.small.text-muted');
                if (justificationEl) justification = justificationEl.textContent.trim();
            }

            // Store the original criteria mark
            criteriaMarks.push({
                text: criteriaText,
                criteria: criteriaText,
                score: score,
                justification: justification
            });
        }
    });

    // Try to find criteria marks from the backend
    // These are typically stored in a hidden div or data attribute on the page
    const criteriaDataElement = document.querySelector('#criteria-data, .criteria-data');
    const hiddenCriteria = document.querySelectorAll('.hidden-criteria, .criteria-item[style*="display: none"]');
    
    // Check for server-rendered criteria
    if (criteriaDataElement || hiddenCriteria.length > 0) {
        console.log("Looking for server-rendered criteria data");
        
        // Try to get criteria from data element
        if (criteriaDataElement) {
            try {
                const dataStr = criteriaDataElement.textContent || criteriaDataElement.dataset.criteria;
                if (dataStr) {
                    const parsedData = JSON.parse(dataStr);
                    if (Array.isArray(parsedData) && parsedData.length > 0) {
                        parsedData.forEach(item => {
                            criteriaMarks.push({
                                text: item.criteria || item.text || item.criterion,
                                criteria: item.criteria || item.text || item.criterion,
                                score: item.score || 1,
                                justification: item.justification || ''
                            });
                        });
                        console.log(`Found ${parsedData.length} criteria items in JSON data`);
                    }
                }
            } catch (e) {
                console.error("Error parsing criteria data:", e);
            }
        }
        
        // Try to get criteria from hidden elements
        if (hiddenCriteria.length > 0) {
            console.log(`Found ${hiddenCriteria.length} hidden criteria items`);
            hiddenCriteria.forEach(item => {
                const criteriaText = item.textContent.trim();
                const scoreEl = item.querySelector('.badge, .score');
                const justificationEl = item.querySelector('.justification, .small');
                
                let score = 1; // Default score
                if (scoreEl) {
                    const scoreText = scoreEl.textContent.trim();
                    if (scoreText.includes('0')) score = 0;
                    else if (scoreText.includes('1')) score = 1;
                    else if (scoreText.includes('2')) score = 2;
                }
                
                criteriaMarks.push({
                    text: criteriaText,
                    criteria: criteriaText,
                    score: score,
                    justification: justificationEl ? justificationEl.textContent.trim() : ''
                });
            });
        }
    }
    
    // Look for criteria in server logs or dynamically generated page content
    if (criteriaMarks.length === 0) {
        // Check for server-logged criteria
        const serverDebugElement = document.querySelector('#debug-output, .debug-output, #server-logs, .server-logs');
        if (serverDebugElement) {
            const debugText = serverDebugElement.textContent;
            if (debugText.includes('Processing criterion:')) {
                const criteriaLines = debugText.split('\n').filter(line => line.includes('Processing criterion:'));
                criteriaLines.forEach(line => {
                    const matches = line.match(/Processing criterion: ([^,]+), score: (\d+)/i);
                    if (matches && matches.length >= 3) {
                        const criteriaText = matches[1].trim();
                        const score = parseInt(matches[2]);
                        
                        criteriaMarks.push({
                            text: criteriaText,
                            criteria: criteriaText,
                            score: score,
                            justification: ''
                        });
                    }
                });
                console.log(`Found ${criteriaLines.length} criteria items in server logs`);
            }
        }
    }
    
    // IMPORTANT: Explicitly check for assignment-specific criteria when no criteria marks are found
    if (criteriaMarks.length === 0) {
        // Force-try to check if this is a news article or report
        const contentLower = contentText.toLowerCase();
        
        // Look for headline/title patterns
        if (contentText.split("\n")[0].split(/\s+/).length <= 15) {
            // Check for news article criteria
            const newsArticleCriteria = [
                { text: "Use headline", score: 2, justification: "The article starts with a headline/title." },
                { text: "Write in third person", score: 2, justification: "The article uses third person perspective." },
                { text: "Use formal tone", score: 2, justification: "The article maintains a formal tone." },
                { text: "Use direct speech with correct punctuation", score: 1, justification: "The article contains direct quotes." }
            ];
            
            // Look for typical news report patterns
            if (contentLower.includes("report") || 
                contentLower.includes("news") || 
                contentLower.includes("discovery") || 
                contentLower.includes("reported") || 
                contentLower.includes("article")) {
                
                console.log("Content looks like a news article, using news-specific criteria");
                criteriaMarks.push(...newsArticleCriteria);
            }
        }
    }
    
    // Check if we need to directly look for criteria in the text
    const defaultServerCriteria = [
        "Use headline", 
        "Use formal tone",
        "Use simple and progressive forms of the past tense",
        "Write in third person",
        "Use direct speech with correct punctuation",
        "Organise paragraphs around a key theme or point",
        "Secure use of full stops & capital letters"
    ];
    
    // If we still don't have criteria, check for default ones in the server logs
    if (criteriaMarks.length === 0) {
        console.log("Checking console logs for criteria");
        
        // Manually scan for criteria evidence in the page source
        document.querySelectorAll('*').forEach(el => {
            if (el.textContent && el.textContent.includes('criterion') && el.textContent.includes('score')) {
                try {
                    // See if this element contains JSON data
                    const text = el.textContent.trim();
                    if (text.startsWith('[') && text.endsWith(']')) {
                        const parsed = JSON.parse(text);
                        if (Array.isArray(parsed) && parsed.length > 0 && parsed[0].criterion) {
                            parsed.forEach(item => {
                                criteriaMarks.push({
                                    text: item.criterion,
                                    criteria: item.criterion,
                                    score: item.score || 1,
                                    justification: item.justification || ''
                                });
                            });
                            console.log(`Found ${parsed.length} criteria items in element text`);
                        }
                    }
                } catch (e) {
                    // Not JSON data, continue scanning
                }
            }
        });
    }

    // If we found explicit criteria marks, use them with our highlighting function
    if (criteriaMarks.length > 0) {
        console.log(`Found ${criteriaMarks.length} explicit criteria marks to apply`);
        
        // Helper function to debug and log the criteria marks
        function debugCriteriaMark(mark) {
            console.log(`Processing criteria mark:`);
            console.log(`  Text: ${mark.text || mark.criteria || 'unknown'}`);
            console.log(`  Score: ${mark.score}`);
            console.log(`  Justification: ${mark.justification ? mark.justification.substring(0, 100) + '...' : 'none'}`);
        }
        
        // For each criteria, find examples automatically even if justification exists
        const enhancedCriteriaMarks = criteriaMarks.map(mark => {
            // Log debugging info
            debugCriteriaMark(mark);
            
            // First check if there are explicit examples in the justification
            console.log(`Finding examples for criteria: ${mark.text || mark.criteria}`);
            const justificationExamples = extractExamplesFromJustification(mark.justification || '');
            
            if (justificationExamples.length > 0) {
                // Keep existing justification with explicit examples
                return mark;
            } else {
                // No explicit examples, so find them automatically
                const autoExamples = findExamplesForCriteria(contentText, mark.text);
                
                // Only include examples with high confidence (increased threshold)
                const confidenceThreshold = 0.85;
                const qualityExamples = autoExamples.filter(ex => 
                    !ex.confidence || ex.confidence >= confidenceThreshold);
                
                if (qualityExamples.length > 0) {
                    // Format examples for justification
                    const exampleTexts = qualityExamples
                        .slice(0, 3)
                        .map(ex => `'${ex.text}'`)
                        .join(", ");
                    
                    // Update justification with auto-detected examples
                    const newJustification = mark.justification 
                        ? `${mark.justification} Examples include: ${exampleTexts}`
                        : `Examples include: ${exampleTexts}`;
                    
                    return {
                        ...mark,
                        justification: newJustification,
                        autoDetected: true
                    };
                }
                
                return mark;
            }
        });
        
        // Fix undefined criteria issues before applying highlighting
        const validCriteriaMarks = enhancedCriteriaMarks.map(mark => {
            // Make sure criteria text is set correctly
            if (!mark.criteria && mark.text) {
                mark.criteria = mark.text;
            } else if (!mark.text && mark.criteria) {
                mark.text = mark.criteria;
            }
            // Set a default if still undefined (shouldn't happen but just in case)
            if (!mark.text && !mark.criteria) {
                mark.text = mark.criterion || "Unknown criteria";
                mark.criteria = mark.criterion || "Unknown criteria";
            }
            return mark;
        });
        
        // Apply highlighting with enhanced criteria marks
        const highlightedHtml = highlightText(contentText, validCriteriaMarks);
        textElement.innerHTML = highlightedHtml;
        return; // Exit here - don't do the fallback
    }
    
    // Disable generic word class detection by default - this is what you wanted to eliminate
    // Only enable it if explicitly requested
    const useAutomatedDetection = false; // Set to false to completely disable generic detection
    
    // Check if we should use fallback automated detection
    if (useAutomatedDetection) {
        console.log("Using automated detection as fallback (user requested)");
        
        // Comprehensive criteria categories for automated detection
        const defaultCriteria = [
            // Word classes - Level 1 (Basic)
            { text: "Use pronouns", score: 1, category: "word-classes" },
            { text: "Use adjectives", score: 1, category: "word-classes" },
            { text: "Use adverbs", score: 1, category: "word-classes" },
            { text: "Use simple verbs", score: 1, category: "word-classes" },
            { text: "Use prepositions", score: 1, category: "word-classes" },
            
            // Word classes - Level 2 (Advanced)
            { text: "Use modal verbs", score: 2, category: "word-classes" },
            { text: "Use strong verbs", score: 2, category: "word-classes" },
            { text: "Use adverbial phrases", score: 2, category: "word-classes" },
            
            // Sentence structure - Level 1 (Basic)
            { text: "Use compound sentences", score: 1, category: "sentence-structure" },
            { text: "Use coordinating conjunctions", score: 1, category: "sentence-structure" },
            
            // Sentence structure - Level 2 (Advanced)
            { text: "Use complex sentences", score: 2, category: "sentence-structure" },
            { text: "Use subordinating conjunctions", score: 2, category: "sentence-structure" },
            { text: "Use relative clauses", score: 2, category: "sentence-structure" }
        ];

        // Find examples for each default criteria
        const criteriaWithExamples = defaultCriteria.map(criteria => {
            const examples = findExamplesForCriteria(contentText, criteria.text);
            
            // Filter examples with high confidence (increased threshold)
            const confidenceThreshold = 0.85;
            const qualityExamples = examples.filter(ex => 
                !ex.confidence || ex.confidence >= confidenceThreshold);
            
            // Include detected examples count
            return {
                ...criteria,
                examples: qualityExamples,
                exampleCount: qualityExamples.length
            };
        });

        // Only use criteria that have good examples in the text
        const validCriteria = criteriaWithExamples
            .filter(criteria => criteria.exampleCount > 0)
            .map(criteria => {
                // Format examples for justification
                const exampleTexts = criteria.examples
                    .slice(0, 3)
                    .map(ex => `'${ex.text}'`)
                    .join(", ");
                
                return {
                    text: criteria.text,
                    criteria: criteria.text,
                    score: criteria.score,
                    justification: `AI detected: ${exampleTexts}`,
                    autoDetected: true,
                    category: criteria.category
                };
            });

        // Apply highlighting with valid criteria
        if (validCriteria.length > 0) {
            console.log(`Found ${validCriteria.length} auto-detected criteria to apply`);
            
            // Sort criteria by category for more organized presentation
            validCriteria.sort((a, b) => {
                // First by category
                if (a.category !== b.category) {
                    return a.category.localeCompare(b.category);
                }
                // Then by score (higher score first)
                return b.score - a.score;
            });
            
            const highlightedHtml = highlightText(contentText, validCriteria);
            textElement.innerHTML = highlightedHtml;
        } else {
            console.log("No valid criteria with examples found in the text");
        }
    } else {
        console.log("No criteria found and automated detection is disabled");
    }
}

// Function to save highlights
async function saveHighlights(writingId) {
    if (!writingId || !window.savedHighlights[writingId]) return;

    // Save to local storage
    localStorage.setItem(`highlights-${writingId}`, JSON.stringify(window.savedHighlights[writingId]));

    // Save to server if needed
    try {
        const response = await fetch(`/api/writings/${writingId}/highlights`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                highlights: window.savedHighlights[writingId]
            })
        });
        if (!response.ok) {
            console.error('Failed to save highlights to server');
        }
    } catch (error) {
        console.error('Error saving highlights:', error);
    }
}

// Function to load highlights
async function loadHighlights(writingId) {
    if (!writingId) return [];

    // Try to load from local storage first
    const localHighlights = localStorage.getItem(`highlights-${writingId}`);
    if (localHighlights) {
        return JSON.parse(localHighlights);
    }

    // If not in local storage, try to load from server
    try {
        const response = await fetch(`/api/writings/${writingId}/highlights`);
        if (response.ok) {
            const data = await response.json();
            return data.highlights;
        }
    } catch (error) {
        console.error('Error loading highlights:', error);
    }
    return [];
}

// Function to extract criteria types from feedback statements
function extractCriteriaTypes(statement) {
    const criteriaTypes = [];

    // Map common descriptions to criteria types
    const criteriaPatterns = [
        // Pronouns
        { pattern: /pronoun|I\b|me\b|my\b|you\b|your\b|he\b|she\b|they\b|their\b|them\b/i, type: "Use pronouns" },

        // Sentence structure
        { pattern: /complex sentence|subordinat|clause|because|although|while|when|after|before|if|since/i, type: "Use complex sentence" },
        { pattern: /coordinat|conjunct|and,|but,|for,|nor,|or,|so,|yet,|FANBOYS/i, type: "Use coordinating conjunctions" },
        { pattern: /relative clause|who|whom|whose|which|that/i, type: "Use relative clauses"},
        { pattern: /compound sentence|main clause|independent clause/i, type: "Use compound sentences" },

        // Word classes
        { pattern: /adjective|descriptive|detail|describ/i, type: "Use adjectives" },
        { pattern: /adverb|-ly\b|how|when|where|manner/i, type: "Use adverbs" },
        { pattern: /verb|action|doing word/i, type: "Use strong verbs" },
        { pattern: /modal verb|can|could|may|might|shall|should|will|would/i, type: "Use modal verbs" },
        { pattern: /preposition|about|above|across|at|in|on|to|over|under|with/i, type: "Use prepositions" },
        { pattern: /determiner|article|the|a|an|this|that|these|those/i, type: "Use determiners" },

        // Other language features
        { pattern: /vocabulary|word choice|sophistic|expression|descriptive language/i, type: "Use sophisticated vocabulary" },
        { pattern: /figurative language|simile|metaphor|personification|alliteration/i, type: "Use figurative language" },
        { pattern: /technical term|subject specific|domain specific/i, type: "Use technical terminology" },

        // Mechanics
        { pattern: /spelling|spell/i, type: "Spelling accuracy" },
        { pattern: /punctuat|comma|period|full stop|apostrophe|quotation|exclamation|question mark/i, type: "Punctuation" },
        { pattern: /paragra|structure|organi[sz]|layout/i, type: "Organization and structure" },
        { pattern: /grammar|tense|subject-verb|agreement/i, type: "Grammar" },
        { pattern: /cohesion|coherence|flow|transition|connective/i, type: "Text cohesion" },
        { pattern: /register|form|audience|purpose|tone|formality/i, type: "Appropriate register" }
    ];

    criteriaPatterns.forEach(item => {
        if (item.pattern.test(statement)) {
            criteriaTypes.push(item.type);
        }
    });

    // If no specific criteria found, use the full statement
    if (criteriaTypes.length === 0) {
        criteriaTypes.push(statement);
    }

    return criteriaTypes;
}

// Function to manually highlight selected text
function highlightSelection(e) {
    const selection = window.getSelection();
    const selectedText = selection.toString().trim();

    if (selectedText.length > 0) {
        const textContainer = this.closest('.card-body');
        const color = textContainer.dataset.activeColor;
        const criteriaText = Array.from(textContainer.querySelectorAll('.criteria-mark'))
                               .find(mark => mark.style.backgroundColor === color)?.textContent || 
                           "Custom highlight";

        // Get the original text content
        const originalText = this.textContent;

        // Modified regex to use word boundaries for exact word matching
        // For single words, we enforce word boundaries
        // For phrases, we match exact phrases only
        let regex;
        if (!selectedText.includes(' ')) {
            // For single words, use word boundaries
            regex = new RegExp(`\\b${escapeRegExp(selectedText)}\\b`, 'g');
        } else {
            // For phrases, use exact matching
            regex = new RegExp(escapeRegExp(selectedText), 'g');
        }

        let match;
        let lastIndex = 0;
        let result = '';

        while ((match = regex.exec(originalText)) !== null) {
            // For phrases, check that it's a standalone phrase with proper boundaries
            let isValidMatch = true;

            if (selectedText.includes(' ')) {
                // Check phrase boundaries for multi-word selections
                const phraseStart = match.index;
                const phraseEnd = match.index + selectedText.length;

                // Ensure the phrase starts at a word boundary or the beginning of text
                const phraseStartValid = phraseStart === 0 || !isAlphaNumeric(originalText[phraseStart - 1]);

                // Ensure the phrase ends at a word boundary or the end of text
                const phraseEndValid = phraseEnd === originalText.length || !isAlphaNumeric(originalText[phraseEnd]);

                isValidMatch = phraseStartValid && phraseEndValid;
            }

            if (isValidMatch) {
                // Add text before match
                result += escapeHtml(originalText.substring(lastIndex, match.index));

                // Add highlighted match with ability to remove
                result += `<span class="highlight" style="background-color: ${color}" data-tooltip="${criteriaText}" data-removable="true">`;
                result += escapeHtml(selectedText);
                result += '</span>';

                lastIndex = match.index + selectedText.length;
            }
        }

        // Add remaining text
        if (lastIndex < originalText.length) {
            result += escapeHtml(originalText.substring(lastIndex));
        }

        // Update content with the highlighted version
        this.innerHTML = result;

        // Save this highlight
        if (window.currentWritingId) {
            if (!window.savedHighlights[window.currentWritingId]) {
                window.savedHighlights[window.currentWritingId] = [];
            }

            window.savedHighlights[window.currentWritingId].push({
                text: selectedText,
                color: color,
                tooltip: criteriaText
            });

            // Save highlights
            saveHighlights(window.currentWritingId);
        }

        // Clear selection
        selection.removeAllRanges();
    }
}

// Function to set up text highlighting
function setupTextHighlighting() {
    const toggleButtons = document.querySelectorAll('.toggle-highlight-mode');
    
    // Call applyCriteriaBoxStyles when the page loads to ensure criteria and examples are highlighted
    setTimeout(applyCriteriaBoxStyles, 1000);
    
    // Set up custom tooltips for highlighted examples
    setTimeout(setupTooltipPositioning, 1500);
    
    // Initialize tooltips if Bootstrap is available
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    // Handle highlight removal by click
    document.addEventListener('click', function(e) {
        // Only process if we're in highlight mode
        const activeButton = document.querySelector('.toggle-highlight-mode.active');
        if (!activeButton) return;

        const highlight = e.target.closest('.highlight-full, .highlight-partial');
        if (highlight && highlight.dataset.removable === 'true') {
            // Check if ctrl/cmd key is pressed (for safety - optional override)
            if (e.ctrlKey || e.metaKey) {
                // Get the plain text content
                const textContent = highlight.textContent;

                // Replace the highlight with plain text
                const textNode = document.createTextNode(textContent);
                highlight.parentNode.replaceChild(textNode, highlight);

                // Prevent default behavior
                e.preventDefault();
                e.stopPropagation();
            }
        }
    });
    
    toggleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const textContainer = this.closest('.card-body');
            if (!textContainer) return;

            const highlightControls = textContainer.querySelector('.highlight-controls');
            const textElement = textContainer.querySelector('.sample-text, .extracted-text');

            if (!highlightControls || !textElement) return;

            const isActive = this.classList.toggle('active');
            highlightControls.style.display = isActive ? 'block' : 'none';

            if (isActive) {
                // Update button state
                this.innerHTML = '<i class="fa fa-times me-1"></i> Exit Marking Mode';
                this.classList.remove('btn-outline-primary');
                this.classList.add('btn-primary');

                // Enable text selection for highlighting
                textElement.style.userSelect = 'text';

                // Try to get a writing ID
                window.currentWritingId = textElement.id ? textElement.id.replace('text-', '') : 
                                          textContainer.dataset.writingId || null;

                // Setup color buttons
                const colorButtons = textContainer.querySelectorAll('.color-button, .color-btn');
                colorButtons.forEach(colorBtn => {
                    colorBtn.addEventListener('click', function() {
                        colorButtons.forEach(btn => btn.classList.remove('active'));
                        this.classList.add('active');
                        textContainer.dataset.activeColor = this.style.backgroundColor || this.dataset.color || '#ffff00';
                    });
                });

                // Set default color if color buttons exist
                if (colorButtons.length > 0) {
                    colorButtons[0].click();
                } else {
                    // Set a default color if no buttons
                    textContainer.dataset.activeColor = '#ffff00';
                }

                // Apply AI highlights if requested, but only when explicitly clicked
                // The dataset.applyAiHighlights attribute is set to 'true' by the template
                // when the button with id 'toggle-highlight-mode' is clicked
                if (this.dataset.applyAiHighlights === 'true' && this.id === 'toggle-highlight-mode') {
                    console.log("User explicitly requested highlight mode - applying AI highlights");
                    applyAIHighlights(textElement);
                } else {
                    console.log("Not applying automatic highlights - requires explicit user action");
                }

                // Load existing manual highlights
                if (currentWritingId) {
                    loadHighlights(currentWritingId).then(highlights => {
                        if (highlights && highlights.length > 0) {
                            // Apply manual highlights on top of AI highlights
                            highlights.forEach(highlight => {
                                const tempDiv = document.createElement('div');
                                tempDiv.innerHTML = textElement.innerHTML;

                                // Find and highlight each occurrence using word boundaries
                                const regex = new RegExp(`\\b${escapeRegExp(highlight.text)}\\b`, 'g');
                                let match;
                                let lastIndex = 0;
                                let result = '';
                                const originalText = textElement.textContent;

                                while ((match = regex.exec(originalText)) !== null) {
                                    // Add text before match
                                    result += originalText.substring(lastIndex, match.index);

                                    // Add highlighted match
                                    result += `<span class="highlight" style="background-color: ${highlight.color}" data-tooltip="${highlight.tooltip}" data-removable="true">`;
                                    result += match[0];
                                    result += '</span>';

                                    lastIndex = match.index + highlight.text.length;
                                }

                                // Add remaining text
                                if (lastIndex < originalText.length) {
                                    result += originalText.substring(lastIndex);
                                }

                                textElement.innerHTML = result;
                            });
                        }
                    });
                }

                // Setup highlighting on selection
                textElement.addEventListener('mouseup', highlightSelection);

                // Setup clear highlights button
                const clearButton = textContainer.querySelector('.clear-highlights');
                if (clearButton) {
                    clearButton.addEventListener('click', function() {
                        textElement.innerHTML = escapeHtml(textElement.textContent);
                        if (window.currentWritingId) {
                            window.savedHighlights[window.currentWritingId] = [];
                            saveHighlights(window.currentWritingId);
                        }
                    });
                }

                // Removed the Ctrl+Click instructions as requested

                // Setup dynamic tooltips for highlights
                document.addEventListener('mouseover', function(e) {
                    const highlight = e.target.closest('.highlight, .highlight-full, .highlight-partial');
                    if (highlight) {
                        const tooltipText = highlight.dataset.tooltip;
                        if (tooltipText) {
                            const rect = highlight.getBoundingClientRect();
                            const tooltip = createTooltip(
                                tooltipText,
                                rect.left + window.scrollX,
                                rect.top + window.scrollY
                            );
                            highlight.addEventListener('mouseout', () => tooltip.remove());
                        }
                    }
                });
            } else {
                // Reset button state
                this.innerHTML = '<i class="fa fa-highlighter me-1"></i> Marking Mode';
                this.classList.remove('btn-primary');
                this.classList.add('btn-outline-primary');

                // Disable selection mode
                textElement.style.userSelect = 'auto';
                textElement.removeEventListener('mouseup', highlightSelection);
            }
        });
    });
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', function() {
    // Only set up the event listener once to avoid duplicate listeners
    if (!window.highlightingInitialized) {
        window.highlightingInitialized = true;
        setupConfidenceIndicators();

        // Re-initialize highlighting when new content is loaded dynamically
        document.addEventListener('DOMNodeInserted', function(e) {
            if (e.target && e.target.classList && 
                (e.target.classList.contains('sample-text') || 
                 e.target.classList.contains('extracted-text'))) {
                setupTextHighlighting();
            }
        });
    }
});

// Function to set up confidence indicators
function setupConfidenceIndicators() {
    // Listen for updates to writing-age
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList' && 
                (mutation.target.id === 'writing-age' || 
                 mutation.target.id === 'feedback-section')) {
                updateConfidenceBadges();
            }
        });
    });

    // Observe the writing-age element for changes
    const writingAgeElement = document.getElementById('writing-age');
    if (writingAgeElement) {
        observer.observe(writingAgeElement, { childList: true });
    }

    // Observe the feedback section for changes
    const feedbackSection = document.getElementById('feedback-section');
    if (feedbackSection) {
        observer.observe(feedbackSection, { childList: true });
    }
}

// Function to update confidence badges
function updateConfidenceBadges() {
    const confidenceBadge = document.getElementById('confidence-badge');
    const validationBadge = document.getElementById('validation-badge');

    if (!confidenceBadge || !validationBadge) return;

    // Get confidence data from data attributes (set by the backend)
    const resultsCard = document.querySelector('.results-card');
    if (!resultsCard) return;

    const confidence = parseFloat(resultsCard.dataset.confidence || "0");
    const validation = resultsCard.dataset.validation || "UNCERTAIN";

    // Update confidence badge
    if (confidence > 0.8) {
        confidenceBadge.textContent = "High Confidence";
        confidenceBadge.className = "badge bg-success";
    } else if (confidence > 0.5) {
        confidenceBadge.textContent = "Medium Confidence";
        confidenceBadge.className = "badge bg-warning";
    } else {
        confidenceBadge.textContent = "Low Confidence";
        confidenceBadge.className = "badge bg-danger";
    }

    // Update validation badge
    if (validation === "VERIFIED") {
        validationBadge.textContent = "Verified";
        validationBadge.className = "badge bg-info";
    } else if (validation === "UNCERTAIN") {
        validationBadge.textContent = "Uncertain";
        validationBadge.className = "badge bg-secondary";
    } else if (validation === "QUESTIONABLE") {
        validationBadge.textContent = "Review Needed";
        validationBadge.className = "badge bg-danger";
    } else {
        validationBadge.style.display = "none";
    }
}

// Function to save highlighted text as WAGOLL example
function saveAsWagoll(textContent, writingId, assignmentId) {
    // Store content globally so other pages can access it
    if (typeof window.currentWritingContent !== 'undefined') {
        window.currentWritingContent = textContent;
    }

    // Get the current highlighted text
    const highlightedContent = textContent;

    // Check if we have content
    if (!highlightedContent) {
        alert('No content to save as WAGOLL');
        return;
    }

    // Create modal for WAGOLL details
    const modalHTML = `
    <div class="modal fade" id="saveWagollModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Save as WAGOLL Example</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div class="mb-3">
                        <label for="wagollTitle" class="form-label">Title</label>
                        <input type="text" class="form-control" id="wagollTitle" required>
                    </div>
                    <div class="mb-3">
                        <label for="wagollExplanation" class="form-label">Why is this a good example?</label>
                        <textarea class="form-control" id="wagollExplanation" rows="3"></textarea>
                    </div>
                    <div class="mb-3 form-check">
                        <input type="checkbox" class="form-check-input" id="wagollIsPublic">
                        <label class="form-check-label" for="wagollIsPublic">Make this example public</label>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" id="saveWagollBtn">Save</button>
                </div>
            </div>
        </div>
    </div>`;

    // Remove existing modal if it exists
    const existingModal = document.getElementById('saveWagollModal');
    if (existingModal) {
        existingModal.remove();
    }

    // Add modal to body
    document.body.insertAdjacentHTML('beforeend', modalHTML);

    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('saveWagollModal'));
    modal.show();

    // Handle save button click
    document.getElementById('saveWagollBtn').onclick = function() {
        const title = document.getElementById('wagollTitle').value;
        const explanation = document.getElementById('wagollExplanation').value;
        const isPublic = document.getElementById('wagollIsPublic').checked;

        if (!title) {
            alert('Please enter a title');
            return;
        }

        console.log("Saving WAGOLL with title:", title);
        console.log("Content:", highlightedContent ? highlightedContent.substring(0, 50) + "..." : "No content");

        // Save to WAGOLL library
        fetch('/wagoll_example/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                title: title,
                content: highlightedContent,
                explanations: explanation,
                is_public: isPublic,
                assignment_id: assignmentId,
                writing_id: writingId
            })
        }).then(response => {
            if (!response.ok) {
                return response.text().then(text => {
                    throw new Error(text || 'Error saving to WAGOLL library');
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                alert('Successfully saved to WAGOLL library!');
                modal.hide();
            } else {
                alert('Failed to save: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error saving to WAGOLL library: ' + error.message);
        });
    };
}

// Export functions for use in other files
window.setupTextHighlighting = setupTextHighlighting;
window.applyAIHighlights = applyAIHighlights;
window.loadHighlights = loadHighlights;
window.highlightText = highlightText;
window.saveAsWagoll = saveAsWagoll;

function createBulletPoints(text) {
    if (!text || text.trim() === '') {
        return '<li>No points available</li>';
    }

    // Split by newlines and process each line
    const lines = text.split('\n')
        .map(line => line.trim())
        .map(line => {
            // Remove any "Key" instances and convert to UK English
            line = line.replace(/\bKey\b/g, '')
                      .replace(/ize\b/g, 'ise')
                      .replace(/yze\b/g, 'yse')
                      .replace(/izing\b/g, 'ising')
                      .replace(/ization\b/g, 'isation');
            
            // Convert ** text ** to bold
            line = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            
            return line.trim();
        })
        .filter(line => line);

    // If no lines found, return the original text
    if (lines.length === 0) {
        return `<li>${text}</li>`;
    }

    // Filter out lines that state "No strengths identified" or "No areas for development identified"
    // if other points are present
    if (lines.length > 1) {
        lines = lines.filter(line => 
            !line.includes("No strengths identified") && 
            !line.includes("No areas for development identified") &&
            !line.includes("No areas identified")
        );
    }

    // Check if the lines already have bullet points
    const hasBullets = lines.some(line => 
        line.startsWith('-') || line.startsWith('•') || /^\d+\./.test(line)
    );

    if (hasBullets) {
        // Process lines with existing bullet points
        return lines.map(line => {
            // Remove bullet character and trim
            let content = line;
            if (line.startsWith('-') || line.startsWith('•')) {
                content = line.substring(1).trim();
            } else if (/^\d+\./.test(line)) {
                content = line.substring(line.indexOf('.') + 1).trim();
            }
            
            return content ? `<li>${content}</li>` : '';
        }).filter(item => item).join('');
    } else {
        // If no bullet points found, treat each line as a separate point
        return lines.map(line => `<li>${line}</li>`).join('');
    }
}