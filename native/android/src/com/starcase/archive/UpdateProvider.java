package com.starcase.archive;
import android.content.*;import android.database.*;import android.net.Uri;import android.os.*;import android.provider.OpenableColumns;import java.io.*;

// Only one verified app-private APK is exposed, read-only and with a temporary URI grant.
public final class UpdateProvider extends ContentProvider {
 public boolean onCreate(){return true;}
 private File file(Uri uri)throws FileNotFoundException{if(!"com.starcase.archive.updates".equals(uri.getAuthority())||!"/release.apk".equals(uri.getPath())||uri.getQuery()!=null)throw new FileNotFoundException();return new File(getContext().getFilesDir(),"updates/release.apk");}
 @Override public String getType(Uri uri){return "application/vnd.android.package-archive";}
 @Override public ParcelFileDescriptor openFile(Uri uri,String mode)throws FileNotFoundException{if(!"r".equals(mode))throw new FileNotFoundException("Read only");return ParcelFileDescriptor.open(file(uri),ParcelFileDescriptor.MODE_READ_ONLY);}
 @Override public Cursor query(Uri uri,String[] projection,String selection,String[] args,String order){try{File f=file(uri);String[] columns=projection==null?new String[]{OpenableColumns.DISPLAY_NAME,OpenableColumns.SIZE}:projection;MatrixCursor cursor=new MatrixCursor(columns);Object[] values=new Object[columns.length];for(int i=0;i<columns.length;i++)values[i]=OpenableColumns.DISPLAY_NAME.equals(columns[i])?"Starcase-Android.apk":OpenableColumns.SIZE.equals(columns[i])?f.length():null;cursor.addRow(values);return cursor;}catch(Exception e){return null;}}
 @Override public Uri insert(Uri uri,ContentValues values){throw new UnsupportedOperationException();}
 @Override public int update(Uri uri,ContentValues values,String where,String[] args){throw new UnsupportedOperationException();}
 @Override public int delete(Uri uri,String where,String[] args){throw new UnsupportedOperationException();}
}
