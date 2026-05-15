' =============================================================================
' CollectStudentEmails.bas
' Outlook 2019 VBA-Makro
'
' Funktionsweise:
'   1. Durchlaeuft alle E-Mails im Posteingang.
'   2. Identifiziert Absender mit @smail.th-koeln.de Adresse.
'   3. Extrahiert Name und E-Mail-Adresse.
'   4. Prueft, ob die Adresse bereits in der students.yaml bekannt ist.
'   5. Fuegt neue Studierende am Ende der YAML-Datei hinzu.
'
' YAML-Format:
'   students:
'   - name: Max Mustermann
'     smail: m.mustermann@smail.th-koeln.de
'     emails: []
'     folders: []
'
' WICHTIG: Den Pfad zur YAML-Datei in YAML_FILE_PATH anpassen!
' =============================================================================

Option Explicit

' Pfad zur YAML-Konfigurationsdatei - bitte anpassen
Private Const YAML_FILE_PATH As String = "D:\TH_Koeln\academic-memory-mcp\students.yaml"

''' Hauptprozedur: Sammelt neue smail-Adressen aus dem Posteingang und speichert
''' sie in der YAML-Datei.
Public Sub CollectSmailAddresses()
    Dim inbox      As Outlook.MAPIFolder
    Dim items      As Outlook.items
    Dim item       As Object
    Dim existing   As Object ' Dictionary: smail_lower -> True
    Dim newStudents As Object ' Dictionary: smail_lower -> DisplayName

    Set existing = LoadExistingSmailAddresses(YAML_FILE_PATH)
    Set newStudents = CreateObject("Scripting.Dictionary")
    newStudents.CompareMode = 1

    Set inbox = Application.Session.GetDefaultFolder(olFolderInbox)
    Set items = inbox.items

    Dim i As Long
    For i = items.count To 1 Step -1
        Set item = items.item(i)
        
        If TypeOf item Is Outlook.mailItem Then
            Dim mail As Outlook.mailItem
            Set mail = item
            
            Dim addr As String
            addr = GetSenderEmailAddress(mail)
            
            ' Nur @smail.th-koeln.de Adressen sammeln
            If InStr(addr, "@smail.th-koeln.de") > 0 Then
                If Not existing.Exists(addr) And Not newStudents.Exists(addr) Then
                    Dim displayName As String
                    displayName = GetSenderDisplayName(mail)
                    
                    ' Wenn DisplayName nur die Adresse ist oder kryptisch, 
                    ' versuchen aus der Adresse abzuleiten
                    If InStr(displayName, "@") > 0 Or Len(displayName) < 3 Then
                        displayName = NameFromSmailAddress(addr)
                    End If
                    
                    newStudents.Add addr, displayName
                End If
            End If
        End If
    Next i

    If newStudents.count = 0 Then
        MsgBox "Keine neuen Studierenden-E-Mails gefunden." & vbCrLf & _
               "(Alle bekannten Adressen sind bereits in der YAML-Datei.)", _
               vbInformation, "CollectStudentEmails"
        Exit Sub
    End If

    ' Neue Studierende an YAML-Datei anhaengen
    AppendStudentsToYaml YAML_FILE_PATH, newStudents

    MsgBox "Fertig!" & vbCrLf & _
           newStudents.count & " neue Studierende in YAML geschrieben:" & vbCrLf & _
           YAML_FILE_PATH, vbInformation, "CollectStudentEmails"

    Set newStudents = Nothing
    Set existing = Nothing
End Sub

' =============================================================================
' YAML lesen / schreiben
' =============================================================================

''' Liest alle bereits vorhandenen smail-Adressen aus der YAML-Datei.
'''
''' Args:
'''     yamlPath: Pfad zur YAML-Datei.
'''
''' Returns:
'''     Dictionary mit smail-Adressen (Lowercase) als Keys.
Private Function LoadExistingSmailAddresses(ByVal yamlPath As String) As Object
    Dim dict As Object
    Set dict = CreateObject("Scripting.Dictionary")
    dict.CompareMode = 1

    If Len(Dir(yamlPath)) = 0 Then
        Set LoadExistingSmailAddresses = dict
        Exit Function
    End If

    Dim fileContent As String
    fileContent = ReadUtf8File(yamlPath)
    If Len(fileContent) = 0 Then
        Set LoadExistingSmailAddresses = dict
        Exit Function
    End If

    Dim allLines() As String
    allLines = Split(fileContent, vbLf)
    
    Dim iLine As Long
    For iLine = 0 To UBound(allLines)
        Dim line As String
        line = Trim(allLines(iLine))
        If Right(line, 1) = vbCr Then line = Left(line, Len(line) - 1)

        ' Suche nach "smail:" Zeilen
        If Left(line, 7) = "smail: " Then
            Dim addr As String
            addr = Trim(Mid(line, 8))
            ' Anfuehrungszeichen entfernen
            addr = Replace(addr, """", "")
            addr = LCase(addr)
            If Len(addr) > 0 And Not dict.Exists(addr) Then
                dict.Add addr, True
            End If
        End If
    Next iLine

    Set LoadExistingSmailAddresses = dict
End Function

''' Haengt neue Studierende an die YAML-Datei an.
'''
''' Args:
'''     yamlPath:    Pfad zur YAML-Datei.
'''     newStudents: Dictionary smail -> DisplayName.
Private Sub AppendStudentsToYaml(ByVal yamlPath As String, _
                                 ByVal newStudents As Object)
    On Error GoTo WriteError

    Dim fileExists As Boolean
    fileExists = (Len(Dir(yamlPath)) > 0)

    ' Bestehenden Inhalt einlesen oder Header vorbereiten
    Dim content As String
    If Not fileExists Then
        content = "students:" & vbLf
    Else
        Dim streamIn As Object
        Set streamIn = CreateObject("ADODB.Stream")
        streamIn.CharSet = "UTF-8"
        streamIn.Open
        streamIn.LoadFromFile yamlPath
        content = streamIn.ReadText
        streamIn.Close
        ' Sicherstellen dass Datei mit Zeilenumbruch endet
        If Right(content, 1) <> vbLf Then content = content & vbLf
    End If

    ' Neue Eintraege anhaengen
    Dim key As Variant
    For Each key In newStudents.Keys
        Dim smailAddr   As String
        Dim displayName As String
        smailAddr = CStr(key)
        displayName = Replace(CStr(newStudents(key)), """", "'")

        content = content & "- name: " & displayName & vbLf
        content = content & "  smail: " & smailAddr & vbLf
        content = content & "  emails: []" & vbLf
        content = content & "  folders: []" & vbLf
        content = content & vbLf
    Next key

    ' UTF-8 ohne BOM schreiben
    Dim streamOut As Object
    Set streamOut = CreateObject("ADODB.Stream")
    streamOut.CharSet = "UTF-8"
    streamOut.Open
    streamOut.WriteText content
    streamOut.Position = 0
    streamOut.Type = 1 ' adTypeBinary
    streamOut.Position = 3 ' UTF-8 BOM ueberspringen
    Dim streamFinal As Object
    Set streamFinal = CreateObject("ADODB.Stream")
    streamFinal.Type = 1
    streamFinal.Open
    streamOut.CopyTo streamFinal
    streamFinal.SaveToFile yamlPath, 2 ' 2 = adSaveCreateOverWrite
    streamOut.Close
    streamFinal.Close
    Exit Sub

WriteError:
    MsgBox "Fehler beim Schreiben der YAML-Datei: " & Err.Description, _
           vbCritical, "CollectStudentEmails"
End Sub

' =============================================================================
' Hilfsfunktionen
' =============================================================================

''' Ermittelt die SMTP-E-Mail-Adresse des Absenders.
'''
''' Args:
'''     mail: Das MailItem.
'''
''' Returns:
'''     SMTP-Adresse (Lowercase).
Private Function GetSenderEmailAddress(ByVal mail As Outlook.mailItem) As String
    On Error GoTo FallbackToProperty

    Dim addrEntry As Outlook.AddressEntry
    Set addrEntry = mail.Sender

    If Not addrEntry Is Nothing Then
        If addrEntry.AddressEntryUserType = olExchangeUserAddressEntry Or _
           addrEntry.AddressEntryUserType = olExchangeRemoteUserAddressEntry Then
            Dim exchUser As Outlook.ExchangeUser
            Set exchUser = addrEntry.GetExchangeUser()
            If Not exchUser Is Nothing Then
                GetSenderEmailAddress = LCase(exchUser.PrimarySmtpAddress)
                Exit Function
            End If
        End If
    End If

FallbackToProperty:
    GetSenderEmailAddress = LCase(mail.SenderEmailAddress)
End Function

''' Ermittelt den Anzeigenamen des Absenders.
'''
''' Args:
'''     mail: Das MailItem.
'''
''' Returns:
'''     Anzeigename.
Private Function GetSenderDisplayName(ByVal mail As Outlook.mailItem) As String
    On Error GoTo FallbackToProperty

    Dim addrEntry As Outlook.AddressEntry
    Set addrEntry = mail.Sender

    If Not addrEntry Is Nothing Then
        If Len(Trim(addrEntry.name)) > 0 Then
            GetSenderDisplayName = Trim(addrEntry.name)
            Exit Function
        End If
    End If

FallbackToProperty:
    GetSenderDisplayName = Trim(mail.SenderName)
End Function

''' Leitet einen Namen aus der smail-Adresse ab.
'''
''' Args:
'''     smailAddr: Die E-Mail-Adresse.
'''
''' Returns:
'''     Kapitalisierter Name.
Private Function NameFromSmailAddress(ByVal smailAddr As String) As String
    Dim atPos As Long
    atPos = InStr(smailAddr, "@")
    if atPos < 2 Then
        NameFromSmailAddress = ""
        Exit Function
    End If
    Dim localPart As String
    localPart = Left(smailAddr, atPos - 1)

    Dim dotPos As Long
    dotPos = InStr(localPart, ".")
    If dotPos < 2 Then
        NameFromSmailAddress = CapitalizeWords(Replace(localPart, "_", " "))
        Exit Function
    End If

    Dim firstPart  As String
    Dim secondPart As String
    firstPart = Left(localPart, dotPos - 1)
    secondPart = Mid(localPart, dotPos + 1)

    Dim fullName As String
    fullName = Replace(firstPart, "_", " ") & " " & Replace(secondPart, "_", " ")
    NameFromSmailAddress = CapitalizeWords(fullName)
End Function

''' Kapitalisiert jedes Wort in einem String.
'''
''' Args:
'''     s: Der Eingabestring.
'''
''' Returns:
'''     String mit kapitalisierten Woertern.
Private Function CapitalizeWords(ByVal s As String) As String
    Dim words()  As String
    Dim i        As Long
    Dim result   As String

    s = Trim(s)
    Do While InStr(s, "  ") > 0
        s = Replace(s, "  ", " ")
    Loop

    words = Split(LCase(s), " ")
    For i = 0 To UBound(words)
        If Len(words(i)) > 0 Then
            words(i) = UCase(Left(words(i), 1)) & Mid(words(i), 2)
        End If
    Next i
    CapitalizeWords = Join(words, " ")
End Function

''' Liest eine UTF-8 Datei ein.
'''
''' Args:
'''     filePath: Pfad zur Datei.
'''
''' Returns:
'''     Inhalt als String.
Private Function ReadUtf8File(ByVal filePath As String) As String
    On Error GoTo ReadErr
    Dim stream As Object
    Set stream = CreateObject("ADODB.Stream")
    stream.CharSet = "UTF-8"
    stream.Open
    stream.LoadFromFile filePath
    ReadUtf8File = stream.ReadText
    stream.Close
    Exit Function
ReadErr:
    ReadUtf8File = ""
End Function
