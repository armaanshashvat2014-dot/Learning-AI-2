# Process latest User Message
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        msg_data = st.session_state.messages[-1]
        with st.chat_message("assistant"):
            think = st.empty(); think.markdown("""<div class="thinking-container"><span class="thinking-text">Thinking</span><div class="thinking-dots"><div class="thinking-dot"></div><div class="thinking-dot"></div><div class="thinking-dot"></div></div></div>""", unsafe_allow_html=True)
            
            try:
                # 1. Gather Text History
                valid_history =[]
                exp_role = "model"
                for m in reversed([m for m in st.session_state.messages[:-1] if not m.get("is_greeting")]):
                    r = "user" if m.get("role") == "user" else "model"
                    txt = m.get("content") or ""
                    if txt.strip() and r == exp_role:
                        valid_history.insert(0, types.Content(role=r, parts=[types.Part.from_text(text=txt)]))
                        exp_role = "user" if exp_role == "model" else "model"
                if valid_history and valid_history[0].role == "model": valid_history.pop(0)

                # 2. RAG BOOK SELECTION
                curr_parts =[]
                books = select_relevant_books(" ".join([m.get("content","") for m in st.session_state.messages[-3:]]), st.session_state.textbook_handles)
                
                # Show the user exactly what is happening!
                if books:
                    st.caption(f"📚 **Reading Textbooks:** {', '.join([get_friendly_name(b.display_name) for b in books])}")
                    for b in books: 
                        curr_parts.append(types.Part.from_uri(file_uri=b.uri, mime_type="application/pdf"))
                
                if f_bytes := msg_data.get("user_attachment_bytes"):
                    mime = msg_data.get("user_attachment_mime") or guess_mime(msg_data.get("user_attachment_name"))
                    if is_image_mime(mime): curr_parts.append(types.Part.from_bytes(data=f_bytes, mime_type=mime))
                    elif "pdf" in mime:
                        tmp = f"temp_{time.time()}.pdf"
                        with open(tmp, "wb") as f: f.write(f_bytes)
                        up = client.files.upload_file(tmp)
                        while up.state.name == "PROCESSING": time.sleep(1); up = client.files.get(name=up.name)
                        curr_parts.append(types.Part.from_uri(file_uri=up.uri, mime_type="application/pdf"))
                        os.remove(tmp)

                # Explicitly order the AI to use the books
                curr_parts.append(types.Part.from_text(text=f"Please analyze the attached Cambridge textbooks and files to answer the user's query. If the answer exists in the book, you MUST use the book's facts and terminology.\n\nUser Query: {msg_data.get('content')}"))
                
                # 3. Generate
                resp = client.models.generate_content(
                    model="gemini-3.1-flash-lite-preview",
                    contents=valid_history +[types.Content(role="user", parts=curr_parts)],
                    config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION, temperature=0.3, tools=[{"google_search": {}}])
                )
                bot_txt = safe_response_text(resp) or "⚠️ *Failed to generate text.*"
                
                # Analytics Extraction
                if am := re.search(r"\[ANALYTICS:\s*({.*?})\s*\]", bot_txt, flags=re.IGNORECASE|re.DOTALL):
                    try:
                        ad = json.loads(am.group(1))
                        bot_txt = bot_txt[:am.start()].strip()
                        if is_authenticated and db: db.collection("users").document(user_email).collection("analytics").add({"timestamp": time.time(), **ad})
                    except Exception: pass

                think.empty()
                
                # Images Extraction
                imgs, mods = [],[]
                if v_prompts := re.findall(r"(IMAGE_GEN|PIE_CHART):\s*\[(.*?)\]", bot_txt):
                    with concurrent.futures.ThreadPoolExecutor(5) as exe:
                        for r in exe.map(process_visual_wrapper, v_prompts):
                            if r and r[0]: imgs.append(r[0]); mods.append(r[1])
                            else: imgs.append(None); mods.append("Failed")
                
                dl = bool(re.search(r"\[PDF_READY\]", bot_txt, re.IGNORECASE))
                st.session_state.messages.append({"role": "assistant", "content": bot_txt, "is_downloadable": dl, "images": imgs, "image_models": mods})
                
                if is_authenticated and sum(1 for m in st.session_state.messages if m["role"] == "user") == 1:
                    t = generate_chat_title(client, st.session_state.messages)
                    if t: get_threads_collection().document(st.session_state.current_thread_id).set({"title": t}, merge=True)
                
                save_chat_history(); st.rerun()
                
            except Exception as e: think.empty(); st.error(f"Error: {e}")
