from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Notes, Video, User
from app.api.v1.notes import generate_notes
from app.schemas.schemas import NotesRequest
from app.auth.auth_handler import get_current_user
import io
from app.auth.rate_limiter import rate_limit
from typing import Optional

router = APIRouter(prefix="/pdf", tags=["PDF Services"])

@router.get("/export", dependencies=[Depends(rate_limit(limit_override=5))])
async def export_pdf(
  video_id: str = Query(...),
  token: Optional[str] = Query(None),
  user: Optional[User] = Depends(get_current_user),
  db: Session = Depends(get_db)
):
  # 1. Fetch the video
  video = db.query(Video).filter(Video.youtube_video_id == video_id).first()
  if not video:
    raise HTTPException(status_code=404, detail="Video not ingested. Please ingest first.")

  user_id = user.id if user else None
  
  if not user_id and token:
    try:
      from jose import jwt
      from app.config import settings
      payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
      decoded_user_id = payload.get("user_id")
      if decoded_user_id:
        user_record = db.query(User).filter(User.id == decoded_user_id).first()
        if user_record:
          user = user_record
          user_id = user.id
    except Exception as token_err:
      print(f"PDF Export: Failed to authenticate token from query parameters: {token_err}")
  
  # 2. Get cached notes - prefer detailed, then summary
  note = db.query(Notes).filter(
    Notes.video_id == video.id,
    Notes.user_id == user_id,
    Notes.note_type == "detailed"
  ).first()

  if not note:
    note = db.query(Notes).filter(
      Notes.video_id == video.id,
      Notes.user_id == user_id,
      Notes.note_type == "summary"
    ).first()

  if not note:
    # If no notes exist, generate them synchronously
    try:
      notes_req = NotesRequest(video_id=video_id, format="detailed")
      notes_res = generate_notes(payload=notes_req, user=user, db=db)
      note_text = notes_res.notes
    except Exception as e:
      raise HTTPException(status_code=500, detail=f"Failed to generate notes: {str(e)}")
  else:
    note_text = note.content

  # 3. Compile PDF using ReportLab flowables
  pdf_buffer = io.BytesIO()
  
  try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListItem, ListFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    
    doc = SimpleDocTemplate(
      pdf_buffer,
      pagesize=letter,
      rightMargin=54,
      leftMargin=54,
      topMargin=54,
      bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    
    # Custom premium styles
    title_style = ParagraphStyle(
      "DocTitle",
      parent=styles["Heading1"],
      fontSize=20,
      leading=24,
      textColor="#1e3a8a", # Dark corporate blue
      alignment=TA_CENTER,
      spaceAfter=20
    )
    
    h1_style = ParagraphStyle(
      "DocH1",
      parent=styles["Heading2"],
      fontSize=13,
      leading=17,
      textColor="#1e40af",
      spaceBefore=14,
      spaceAfter=6
    )
    
    h2_style = ParagraphStyle(
      "DocH2",
      parent=styles["Heading3"],
      fontSize=11,
      leading=15,
      textColor="#2563eb",
      spaceBefore=10,
      spaceAfter=4
    )
    
    body_style = ParagraphStyle(
      "DocBody",
      parent=styles["BodyText"],
      fontSize=9.5,
      leading=14,
      textColor="#1e293b",
      spaceAfter=8
    )
    
    bullet_style = ParagraphStyle(
      "DocBullet",
      parent=styles["BodyText"],
      fontSize=9.5,
      leading=14,
      textColor="#1e293b",
      leftIndent=15,
      firstLineIndent=-10,
      spaceAfter=4
    )

    story = []
    
    # Title element
    story.append(Paragraph(f"AI Study Guide: {video.title}", title_style))
    story.append(Spacer(1, 10))
    
    # Custom code block style
    code_block_style = ParagraphStyle(
      "DocCodeBlock",
      parent=styles["BodyText"],
      fontName="Courier",
      fontSize=8.5,
      leading=11,
      textColor="#0f172a",
      backColor="#f1f5f9",
      borderColor="#cbd5e1",
      borderWidth=1,
      borderPadding=8,
      spaceAfter=10
    )

    # Simple Markdown & Custom Structure Parser
    lines = note_text.split("\n")
    in_code_block = False
    code_lines = []

    # Check if there are any ss_ screenshot placeholders in the note text
    has_screenshots = any("](ss_" in line for line in lines)
    stream_url = None
    ffmpeg_path = None
    
    import os
    from pathlib import Path
    TEMP_DIR = Path(__file__).parent.parent.parent / "temp"
    TEMP_DIR.mkdir(exist_ok=True)
    
    if has_screenshots:
      try:
        import subprocess
        from static_ffmpeg import run
        ffmpeg_path, _ = run.get_or_fetch_platform_executables_else_raise()
        print(f"PDF Service: Pre-fetching worst format stream URL for video {video.youtube_video_id}...")
        yt_cmd = ["yt-dlp", "-g", "-f", "worst", f"https://www.youtube.com/watch?v={video.youtube_video_id}"]
        res = subprocess.run(yt_cmd, capture_output=True, text=True, timeout=15)
        if res.returncode == 0:
          stream_url = res.stdout.strip().split("\n")[0]
          print("PDF Service: Stream URL successfully retrieved.")
        else:
          print("PDF Service: yt-dlp returned non-zero exit code:", res.stderr)
      except Exception as e:
        print("PDF Service: Failed to initialize ffmpeg or fetch stream URL:", e)

    for line in lines:
      # Strip spaces for general parsing, but preserve structure inside code blocks
      stripped_line = line.strip()
      
      # Handle code block start/end
      if stripped_line.startswith("```"):
        if in_code_block:
          # End of code block: render it
          code_text = "<br/>".join(code_lines)
          story.append(Paragraph(code_text, code_block_style))
          story.append(Spacer(1, 6))
          in_code_block = False
          code_lines = []
        else:
          in_code_block = True
        continue

      if in_code_block:
        # Escape HTML characters for ReportLab Paragraph rendering safety
        escaped_line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        # Highlight code comments in green
        stripped_code_line = escaped_line.strip()
        if stripped_code_line.startswith("#") or stripped_code_line.startswith("//"):
          escaped_line = f'<font color="#16a34a">{escaped_line}</font>'
        code_lines.append(escaped_line)
        continue

      if not stripped_line:
        continue

      # Image markdown: ![caption](url)
      if stripped_line.startswith("![") and "](" in stripped_line and stripped_line.endswith(")"):
        try:
          alt_start = 2
          alt_end = stripped_line.find("](")
          url_start = alt_end + 2
          url_end = len(stripped_line) - 1
          caption = stripped_line[alt_start:alt_end]
          img_url = stripped_line[url_start:url_end]
          
          # If it is a timestamp screenshot placeholder: ss_123
          if img_url.startswith("ss_") and stream_url and ffmpeg_path:
            try:
              import subprocess
              seconds = int(img_url[3:])
              output_filename = f"frame_{video.youtube_video_id}_{seconds}.jpg"
              output_path = str(TEMP_DIR / output_filename)
              
              extracted = True
              if not os.path.exists(output_path):
                h = seconds // 3600
                m = (seconds % 3600) // 60
                s = seconds % 60
                time_str = f"{h:02d}:{m:02d}:{s:02d}"
                
                print(f"PDF Service: Extracting video frame at {time_str} ({seconds}s)...")
                ff_cmd = [
                  ffmpeg_path,
                  "-ss", time_str,
                  "-i", stream_url,
                  "-vframes", "1",
                  "-q:v", "4",
                  "-y",
                  output_path
                ]
                ff_res = subprocess.run(ff_cmd, capture_output=True, timeout=10)
                extracted = (ff_res.returncode == 0)
              
              if extracted and os.path.exists(output_path):
                from reportlab.platypus import Image
                img = Image(output_path, width=440, height=248)
                story.append(img)
                story.append(Spacer(1, 4))
                
                caption_style = ParagraphStyle(
                  "ImgCaption",
                  parent=styles["BodyText"],
                  fontSize=8,
                  textColor="#64748b",
                  alignment=TA_CENTER,
                  spaceAfter=12
                )
                story.append(Paragraph(caption, caption_style))
                continue
            except Exception as e:
              print("PDF Service: Error extracting/rendering video frame:", e)

          # Otherwise fallback to remote URL download
          import requests
          from io import BytesIO
          from reportlab.platypus import Image
          
          resp = requests.get(img_url, timeout=5)
          if resp.ok:
            img = Image(BytesIO(resp.content), width=440, height=248)
            story.append(img)
            story.append(Spacer(1, 4))
            
            caption_style = ParagraphStyle(
              "ImgCaption",
              parent=styles["BodyText"],
              fontSize=8,
              textColor="#64748b",
              alignment=TA_CENTER,
              spaceAfter=12
            )
            story.append(Paragraph(caption, caption_style))
        except Exception as img_err:
          print("PDF Service: Failed to fetch or embed image:", img_err)
        continue

      # Heading 1 (legacy # prefix)
      if stripped_line.startswith("# "):
        text = stripped_line[2:]
        story.append(Paragraph(text, h1_style))
      # Heading 2 (legacy ## prefix)
      elif stripped_line.startswith("## "):
        text = stripped_line[3:]
        story.append(Paragraph(text, h2_style))
      # Heading 3 (legacy ### prefix)
      elif stripped_line.startswith("### "):
        text = stripped_line[4:]
        story.append(Paragraph(text, h2_style))
      # Custom Headings (All caps or ending in colon) without markdown symbols
      elif not stripped_line.startswith("- ") and (
        (stripped_line.isupper() and len(stripped_line) < 60 and len(stripped_line) > 3) or 
        (stripped_line.endswith(":") and len(stripped_line) < 60 and len(stripped_line) > 3)
      ):
        text = stripped_line[:-1] if stripped_line.endswith(":") else stripped_line
        story.append(Paragraph(text, h1_style))
      # Bullet points (dashes or legacy asterisks)
      elif stripped_line.startswith("- ") or stripped_line.startswith("* "):
        text = stripped_line[2:]
        story.append(Paragraph(f"&bull; {text}", bullet_style))
      # Normal body text
      else:
        text = stripped_line.replace("**", "<b>", 1).replace("**", "</b>", 1)
        story.append(Paragraph(text, body_style))
        
    doc.build(story)
    
  except Exception as reportlab_err:
    print("PDF Service: ReportLab compilation error, falling back to plaintext stream:", reportlab_err)
    # Fallback to write string contents directly to stream
    pdf_buffer = io.BytesIO()
    pdf_buffer.write(f"YouTube AI Learning Workspace Study Guide\n\nVideo: {video.title}\nID: {video_id}\n\n".encode("utf-8"))
    pdf_buffer.write(note_text.encode("utf-8"))
    
  pdf_buffer.seek(0)
  
  return StreamingResponse(
    pdf_buffer,
    media_type="application/pdf",
    headers={"Content-Disposition": f"attachment; filename=study_notes_{video_id}.pdf"}
  )
